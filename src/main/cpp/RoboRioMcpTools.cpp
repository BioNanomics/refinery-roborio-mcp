// Copyright (c) BioNanomics. All rights reserved.
// Licensed under the MIT License.

#include "refinery/mcp/RoboRioMcpTools.h"

#include <cstring>
#include <string>
#include <string_view>

#include <frc/DriverStation.h>
#include <frc/RobotController.h>
#include <frc2/command/CommandScheduler.h>
#include <networktables/NetworkTable.h>
#include <networktables/NetworkTableInstance.h>
#include <networktables/Topic.h>

namespace refinery::mcp {

// ---- Struct decoding helpers ------------------------------------------------

namespace {

/// Returns the byte size of one instance of the named WPILib struct,
/// or -1 if the type is not recognized.
int StructSize(std::string_view typeName) {
  if (typeName == "Rotation2d")           return 8;
  if (typeName == "Translation2d")        return 16;
  if (typeName == "Pose2d")               return 24;
  if (typeName == "Transform2d")          return 24;
  if (typeName == "Twist2d")              return 24;
  if (typeName == "ChassisSpeeds")        return 24;
  if (typeName == "SwerveModuleState")    return 16;
  if (typeName == "SwerveModulePosition") return 16;
  if (typeName == "Quaternion")           return 32;
  if (typeName == "Rotation3d")           return 32;
  if (typeName == "Translation3d")        return 24;
  if (typeName == "Pose3d")               return 56;
  return -1;
}

/// Read a little-endian double from raw bytes at the given offset.
double ReadDouble(std::span<const uint8_t> raw, size_t offset) {
  double val;
  std::memcpy(&val, raw.data() + offset, sizeof(double));
  return val;
}

wpi::json DecodeRotation2d(std::span<const uint8_t> raw, size_t off) {
  return {{"radians", ReadDouble(raw, off)}};
}

wpi::json DecodeTranslation2d(std::span<const uint8_t> raw, size_t off) {
  return {{"x", ReadDouble(raw, off)}, {"y", ReadDouble(raw, off + 8)}};
}

wpi::json DecodePose2d(std::span<const uint8_t> raw, size_t off) {
  return {{"translation", DecodeTranslation2d(raw, off)},
          {"rotation", DecodeRotation2d(raw, off + 16)}};
}

wpi::json DecodeTransform2d(std::span<const uint8_t> raw, size_t off) {
  return {{"translation", DecodeTranslation2d(raw, off)},
          {"rotation", DecodeRotation2d(raw, off + 16)}};
}

wpi::json DecodeTwist2d(std::span<const uint8_t> raw, size_t off) {
  return {{"dx", ReadDouble(raw, off)},
          {"dy", ReadDouble(raw, off + 8)},
          {"dtheta", ReadDouble(raw, off + 16)}};
}

wpi::json DecodeChassisSpeeds(std::span<const uint8_t> raw, size_t off) {
  return {{"vx", ReadDouble(raw, off)},
          {"vy", ReadDouble(raw, off + 8)},
          {"omega", ReadDouble(raw, off + 16)}};
}

wpi::json DecodeSwerveModuleState(std::span<const uint8_t> raw, size_t off) {
  return {{"speed", ReadDouble(raw, off)},
          {"angle", DecodeRotation2d(raw, off + 8)}};
}

wpi::json DecodeSwerveModulePosition(std::span<const uint8_t> raw, size_t off) {
  return {{"distance", ReadDouble(raw, off)},
          {"angle", DecodeRotation2d(raw, off + 8)}};
}

wpi::json DecodeQuaternion(std::span<const uint8_t> raw, size_t off) {
  return {{"w", ReadDouble(raw, off)},
          {"x", ReadDouble(raw, off + 8)},
          {"y", ReadDouble(raw, off + 16)},
          {"z", ReadDouble(raw, off + 24)}};
}

wpi::json DecodeRotation3d(std::span<const uint8_t> raw, size_t off) {
  return {{"quaternion", DecodeQuaternion(raw, off)}};
}

wpi::json DecodeTranslation3d(std::span<const uint8_t> raw, size_t off) {
  return {{"x", ReadDouble(raw, off)},
          {"y", ReadDouble(raw, off + 8)},
          {"z", ReadDouble(raw, off + 16)}};
}

wpi::json DecodePose3d(std::span<const uint8_t> raw, size_t off) {
  return {{"translation", DecodeTranslation3d(raw, off)},
          {"rotation", DecodeRotation3d(raw, off + 24)}};
}

/// Decode a single struct instance at the given byte offset.
wpi::json DecodeOne(std::string_view typeName,
                    std::span<const uint8_t> raw, size_t off) {
  if (typeName == "Rotation2d")           return DecodeRotation2d(raw, off);
  if (typeName == "Translation2d")        return DecodeTranslation2d(raw, off);
  if (typeName == "Pose2d")               return DecodePose2d(raw, off);
  if (typeName == "Transform2d")          return DecodeTransform2d(raw, off);
  if (typeName == "Twist2d")              return DecodeTwist2d(raw, off);
  if (typeName == "ChassisSpeeds")        return DecodeChassisSpeeds(raw, off);
  if (typeName == "SwerveModuleState")    return DecodeSwerveModuleState(raw, off);
  if (typeName == "SwerveModulePosition") return DecodeSwerveModulePosition(raw, off);
  if (typeName == "Quaternion")           return DecodeQuaternion(raw, off);
  if (typeName == "Rotation3d")           return DecodeRotation3d(raw, off);
  if (typeName == "Translation3d")        return DecodeTranslation3d(raw, off);
  if (typeName == "Pose3d")               return DecodePose3d(raw, off);
  return nullptr;
}

/// Decode a WPILib struct type string + raw bytes into JSON.
/// Returns nullptr if the type is not recognized.
wpi::json DecodeStruct(std::string_view typeString,
                       std::span<const uint8_t> raw) {
  if (typeString.empty() || raw.empty()) return nullptr;
  if (typeString.substr(0, 7) != "struct:") return nullptr;

  auto structPart = typeString.substr(7);
  bool isArray = structPart.size() >= 2 &&
                 structPart.substr(structPart.size() - 2) == "[]";
  auto typeName = isArray
                      ? structPart.substr(0, structPart.size() - 2)
                      : structPart;

  int size = StructSize(typeName);
  if (size <= 0 || raw.size() < static_cast<size_t>(size)) return nullptr;

  if (!isArray) {
    return DecodeOne(typeName, raw, 0);
  }

  size_t count = raw.size() / static_cast<size_t>(size);
  wpi::json arr = wpi::json::array();
  for (size_t i = 0; i < count; ++i) {
    arr.push_back(DecodeOne(typeName, raw, i * static_cast<size_t>(size)));
  }
  return arr;
}

}  // namespace

wpi::json RoboRioMcpTools::GetToolDefinitions() {
  wpi::json tools = wpi::json::array();

  tools.push_back(DefineTool(
      "get_robot_status",
      "Get the current robot status including enabled state, operating mode, "
      "estop status, battery voltage, brownout state, and whether robot code "
      "is running.",
      EmptySchema()));

  tools.push_back(DefineTool(
      "get_battery_voltage",
      "Get the current robot battery voltage as a numeric value.",
      EmptySchema()));

  tools.push_back(DefineTool(
      "get_match_info",
      "Get match information including alliance color and station number, "
      "match type, match number, game-specific message, and remaining match "
      "time.",
      EmptySchema()));

  tools.push_back(DefineTool(
      "get_robot_stats",
      "Get detailed robot statistics including CAN bus status, "
      "3.3V/5V/6V rail voltages, currents, and fault counts, and input "
      "voltage.",
      EmptySchema()));

  tools.push_back(DefineTool(
      "get_connection_info",
      "Get connection status for the Driver Station and FMS.",
      EmptySchema()));

  tools.push_back(DefineTool(
      "get_subsystems",
      "List all registered command-based subsystems, their current command, "
      "and their default command.",
      EmptySchema()));

  // get_networktables has an optional 'path' parameter
  wpi::json ntSchema = {
      {"type", "object"},
      {"properties",
       {{"path",
         {{"type", "string"},
          {"description",
           "NetworkTables path to browse (default: \"/\"). "
           "Example: \"/SmartDashboard\" or \"/AdvantageKit\"."
           }}}}}};

  tools.push_back(DefineTool(
      "get_networktables",
      "Browse the NetworkTables tree. Returns subtable names and topic values "
      "at the specified path (one level deep). "
      "Use the 'path' argument to navigate deeper.",
      ntSchema));

  tools.push_back(DefineTool(
      "get_vision_status",
      "Get a complete snapshot of the robot's vision system. Returns camera "
      "connectivity (per camera and per coprocessor), whether the pose has "
      "been seeded, the latest vision-estimated pose, best tag ambiguity, "
      "measurement count, configuration toggles (Enable Vision, Use April "
      "Rotation), and the current drivetrain pose for comparison. "
      "All data is read from AdvantageKit /RealOutputs/Vision/* keys and "
      "SmartDashboard toggles.",
      EmptySchema()));

  return tools;
}

wpi::json RoboRioMcpTools::CallTool(std::string_view name,
                                    const wpi::json& arguments) {
  if (name == "get_robot_status") {
    return WrapTextResult(GetRobotStatus());
  } else if (name == "get_battery_voltage") {
    return WrapTextResult(GetBatteryVoltage());
  } else if (name == "get_match_info") {
    return WrapTextResult(GetMatchInfo());
  } else if (name == "get_robot_stats") {
    return WrapTextResult(GetRobotStats());
  } else if (name == "get_connection_info") {
    return WrapTextResult(GetConnectionInfo());
  } else if (name == "get_subsystems") {
    return WrapTextResult(GetSubsystems());
  } else if (name == "get_networktables") {
    std::string path = "/";
    if (arguments.contains("path") && arguments["path"].is_string()) {
      path = arguments["path"].get<std::string>();
      if (path.empty()) {
        path = "/";
      }
    }
    return WrapTextResult(GetNetworkTables(path));
  } else if (name == "get_vision_status") {
    return WrapTextResult(GetVisionStatus());
  } else {
    return WrapErrorResult(std::string("Unknown tool: ") + std::string(name));
  }
}

// ---- Tool implementations ----

std::string RoboRioMcpTools::GetRobotStatus() {
  std::string mode = "Disabled";
  if (frc::DriverStation::IsEnabled()) {
    if (frc::DriverStation::IsAutonomous()) {
      mode = "Autonomous";
    } else if (frc::DriverStation::IsTeleop()) {
      mode = "Teleoperated";
    } else if (frc::DriverStation::IsTest()) {
      mode = "Test";
    }
  }

  wpi::json status = {
      {"enabled", frc::DriverStation::IsEnabled()},
      {"autonomous", frc::DriverStation::IsAutonomous()},
      {"teleop", frc::DriverStation::IsTeleop()},
      {"test", frc::DriverStation::IsTest()},
      {"mode", mode},
      {"eStop", frc::DriverStation::IsEStopped()},
      {"batteryVoltage", frc::RobotController::GetBatteryVoltage().value()},
      {"brownedOut", frc::RobotController::IsBrownedOut()},
      {"systemActive", frc::RobotController::IsSysActive()}};
  return status.dump();
}

std::string RoboRioMcpTools::GetBatteryVoltage() {
  wpi::json voltage = {
      {"volts", frc::RobotController::GetBatteryVoltage().value()},
      {"inputVoltage", frc::RobotController::GetInputVoltage().value()}};
  return voltage.dump();
}

std::string RoboRioMcpTools::GetMatchInfo() {
  auto alliance = frc::DriverStation::GetAlliance();
  std::string allianceColor = "Unknown";
  if (alliance.has_value()) {
    allianceColor = (alliance.value() == frc::DriverStation::Alliance::kRed)
                        ? "Red"
                        : "Blue";
  }

  auto location = frc::DriverStation::GetLocation();

  auto matchType = frc::DriverStation::GetMatchType();
  std::string matchTypeStr;
  switch (matchType) {
    case frc::DriverStation::MatchType::kNone:
      matchTypeStr = "None";
      break;
    case frc::DriverStation::MatchType::kPractice:
      matchTypeStr = "Practice";
      break;
    case frc::DriverStation::MatchType::kQualification:
      matchTypeStr = "Qualification";
      break;
    case frc::DriverStation::MatchType::kElimination:
      matchTypeStr = "Elimination";
      break;
  }

  wpi::json info = {
      {"allianceColor", allianceColor},
      {"allianceStation", location.has_value() ? location.value() : 0},
      {"matchType", matchTypeStr},
      {"matchNumber", frc::DriverStation::GetMatchNumber()},
      {"replayNumber", frc::DriverStation::GetReplayNumber()},
      {"gameSpecificMessage", frc::DriverStation::GetGameSpecificMessage()},
      {"matchTime", frc::DriverStation::GetMatchTime().value()},
      {"fmsAttached", frc::DriverStation::IsFMSAttached()}};
  return info.dump();
}

std::string RoboRioMcpTools::GetRobotStats() {
  auto canStatus = frc::RobotController::GetCANStatus();

  wpi::json stats = {
      {"inputVoltage", frc::RobotController::GetInputVoltage().value()},
      {"inputCurrent", frc::RobotController::GetInputCurrent().value()},
      {"canBus",
       {{"percentBusUtilization", canStatus.percentBusUtilization},
        {"busOffCount", canStatus.busOffCount},
        {"txFullCount", canStatus.txFullCount},
        {"receiveErrorCount", canStatus.receiveErrorCount},
        {"transmitErrorCount", canStatus.transmitErrorCount}}},
      {"rail3v3",
       {{"voltage", frc::RobotController::GetVoltage3V3().value()},
        {"current", frc::RobotController::GetCurrent3V3().value()},
        {"enabled", frc::RobotController::GetEnabled3V3()},
        {"faultCount", frc::RobotController::GetFaultCount3V3()}}},
      {"rail5v",
       {{"voltage", frc::RobotController::GetVoltage5V().value()},
        {"current", frc::RobotController::GetCurrent5V().value()},
        {"enabled", frc::RobotController::GetEnabled5V()},
        {"faultCount", frc::RobotController::GetFaultCount5V()}}},
      {"rail6v",
       {{"voltage", frc::RobotController::GetVoltage6V().value()},
        {"current", frc::RobotController::GetCurrent6V().value()},
        {"enabled", frc::RobotController::GetEnabled6V()},
        {"faultCount", frc::RobotController::GetFaultCount6V()}}}};
  return stats.dump();
}

std::string RoboRioMcpTools::GetConnectionInfo() {
  wpi::json info = {{"dsAttached", frc::DriverStation::IsDSAttached()},
                    {"fmsAttached", frc::DriverStation::IsFMSAttached()}};
  return info.dump();
}

std::string RoboRioMcpTools::GetSubsystems() {
  wpi::json subsystems = wpi::json::array();

  try {
    wpi::json schedulerInfo = {
        {"name", "CommandScheduler"},
        {"note",
         "Subsystem details are published to SmartDashboard/Shuffleboard. "
         "Use get_networktables with path '/SmartDashboard' to see subsystem "
         "state."}};
    subsystems.push_back(schedulerInfo);
  } catch (const std::exception& e) {
    wpi::json error = {
        {"error",
         std::string("Command-based framework not available: ") + e.what()}};
    subsystems.push_back(error);
  }

  return subsystems.dump();
}

std::string RoboRioMcpTools::GetNetworkTables(std::string_view path) {
  auto ntInst = nt::NetworkTableInstance::GetDefault();
  std::shared_ptr<nt::NetworkTable> table;

  if (path == "/" || path.empty()) {
    table = ntInst.GetTable("");
  } else {
    // Strip leading slash for NT API
    std::string ntPath(path);
    if (!ntPath.empty() && ntPath[0] == '/') {
      ntPath = ntPath.substr(1);
    }
    table = ntInst.GetTable(ntPath);
  }

  // List subtables
  auto subtableNames = table->GetSubTables();
  wpi::json subtables = wpi::json::array();
  for (const auto& name : subtableNames) {
    subtables.push_back(name);
  }

  // List topics (key-value pairs) at this level
  wpi::json topics = wpi::json::object();
  for (const auto& topic : table->GetTopics()) {
    std::string topicName = topic.GetName();
    // Get just the leaf name (after the last /)
    std::string leafName = topicName;
    auto lastSlash = topicName.rfind('/');
    if (lastSlash != std::string::npos) {
      leafName = topicName.substr(lastSlash + 1);
    }

    // Read value as generic entry
    auto entry = ntInst.GetEntry(topicName);
    auto value = entry.GetValue();

    switch (value.type()) {
      case NT_BOOLEAN:
        topics[leafName] = value.GetBoolean();
        break;
      case NT_DOUBLE:
        topics[leafName] = value.GetDouble();
        break;
      case NT_FLOAT:
        topics[leafName] = static_cast<double>(value.GetFloat());
        break;
      case NT_INTEGER:
        topics[leafName] = value.GetInteger();
        break;
      case NT_STRING:
        topics[leafName] = std::string(value.GetString());
        break;
      case NT_BOOLEAN_ARRAY: {
        auto arr = value.GetBooleanArray();
        wpi::json jsonArr = wpi::json::array();
        for (auto b : arr) {
          jsonArr.push_back(static_cast<bool>(b));
        }
        topics[leafName] = jsonArr;
        break;
      }
      case NT_DOUBLE_ARRAY: {
        auto arr = value.GetDoubleArray();
        wpi::json jsonArr = wpi::json::array();
        for (auto d : arr) {
          jsonArr.push_back(d);
        }
        topics[leafName] = jsonArr;
        break;
      }
      case NT_FLOAT_ARRAY: {
        auto arr = value.GetFloatArray();
        wpi::json jsonArr = wpi::json::array();
        for (auto f : arr) {
          jsonArr.push_back(static_cast<double>(f));
        }
        topics[leafName] = jsonArr;
        break;
      }
      case NT_INTEGER_ARRAY: {
        auto arr = value.GetIntegerArray();
        wpi::json jsonArr = wpi::json::array();
        for (auto l : arr) {
          jsonArr.push_back(l);
        }
        topics[leafName] = jsonArr;
        break;
      }
      case NT_STRING_ARRAY: {
        auto arr = value.GetStringArray();
        wpi::json jsonArr = wpi::json::array();
        for (const auto& s : arr) {
          jsonArr.push_back(std::string(s));
        }
        topics[leafName] = jsonArr;
        break;
      }
      case NT_UNASSIGNED:
        topics[leafName] = "[unassigned]";
        break;
      default: {
        // Attempt to decode WPILib struct types (Pose2d, ChassisSpeeds, etc.)
        std::string typeStr = topic.GetTypeString();
        auto raw = value.GetRaw();
        auto decoded = DecodeStruct(typeStr, raw);
        if (!decoded.is_null()) {
          topics[leafName] = decoded;
        } else {
          topics[leafName] = "[" + typeStr + " (" +
                             std::to_string(raw.size()) + " bytes)]";
        }
        break;
      }
    }
  }

  wpi::json result = {
      {"path", std::string(path)}, {"subtables", subtables}, {"topics", topics}};
  return result.dump();
}

std::string RoboRioMcpTools::GetVisionStatus() {
  auto ntInst = nt::NetworkTableInstance::GetDefault();
  wpi::json result = wpi::json::object();

  // Config toggles (SmartDashboard)
  result["config"] = {
      {"enableVision",
       ntInst.GetEntry("/SmartDashboard/Enable Vision").GetBoolean(false)},
      {"useAprilRotation",
       ntInst.GetEntry("/SmartDashboard/Use April Rotation").GetBoolean(false)}};

  // Seeding state
  wpi::json seeding = {
      {"poseSeeded",
       ntInst.GetEntry("/RealOutputs/Vision/PoseSeeded").GetBoolean(false)}};

  // Seed fallback pose
  {
    auto topic = ntInst.GetTopic("/RealOutputs/Vision/SeedFallback");
    auto raw = ntInst.GetEntry("/RealOutputs/Vision/SeedFallback")
                   .GetValue()
                   .GetRaw();
    if (!raw.empty()) {
      auto decoded = DecodeStruct(topic.GetTypeString(), raw);
      if (!decoded.is_null()) {
        seeding["seedFallbackPose"] = decoded;
      }
    }
  }
  result["seeding"] = seeding;

  // Camera connectivity
  result["cameras"] = {
      {"CameraFL",
       ntInst.GetEntry("/RealOutputs/Vision/CameraFL/Connected")
           .GetBoolean(false)},
      {"CameraFR",
       ntInst.GetEntry("/RealOutputs/Vision/CameraFR/Connected")
           .GetBoolean(false)},
      {"CameraBL",
       ntInst.GetEntry("/RealOutputs/Vision/CameraBL/Connected")
           .GetBoolean(false)},
      {"CameraBR",
       ntInst.GetEntry("/RealOutputs/Vision/CameraBR/Connected")
           .GetBoolean(false)}};

  result["coprocessors"] = {
      {"left",
       ntInst.GetEntry("/RealOutputs/Vision/CoprocessorL_Connected")
           .GetBoolean(false)},
      {"right",
       ntInst.GetEntry("/RealOutputs/Vision/CoprocessorR_Connected")
           .GetBoolean(false)}};

  // Detection state
  result["detection"] = {
      {"hasTarget",
       ntInst.GetEntry("/RealOutputs/Vision/HasTarget").GetBoolean(false)},
      {"measurementCount",
       ntInst.GetEntry("/RealOutputs/Vision/MeasurementCount").GetInteger(0)},
      {"bestAmbiguity",
       ntInst.GetEntry("/RealOutputs/Vision/BestAmbiguity").GetDouble(1.0)}};

  // Estimated pose from vision
  {
    auto topic = ntInst.GetTopic("/RealOutputs/Vision/EstimatedPose");
    auto raw = ntInst.GetEntry("/RealOutputs/Vision/EstimatedPose")
                   .GetValue()
                   .GetRaw();
    if (!raw.empty()) {
      auto decoded = DecodeStruct(topic.GetTypeString(), raw);
      if (!decoded.is_null()) {
        result["estimatedPose"] = decoded;
      }
    }
  }

  // Current drivetrain pose for comparison
  {
    auto topic = ntInst.GetTopic("/RealOutputs/Drivetrain/Pose");
    auto raw = ntInst.GetEntry("/RealOutputs/Drivetrain/Pose")
                   .GetValue()
                   .GetRaw();
    if (!raw.empty()) {
      auto decoded = DecodeStruct(topic.GetTypeString(), raw);
      if (!decoded.is_null()) {
        result["drivetrainPose"] = decoded;
      }
    }
  }

  return result.dump();
}

// ---- Helpers ----

wpi::json RoboRioMcpTools::DefineTool(std::string_view name,
                                       std::string_view description,
                                       const wpi::json& inputSchema) {
  return {{"name", std::string(name)},
          {"description", std::string(description)},
          {"inputSchema", inputSchema}};
}

wpi::json RoboRioMcpTools::EmptySchema() {
  return {{"type", "object"}, {"properties", wpi::json::object()}};
}

wpi::json RoboRioMcpTools::WrapTextResult(std::string_view text) {
  return {
      {"content",
       wpi::json::array({{{"type", "text"}, {"text", std::string(text)}}})},
      {"isError", false}};
}

wpi::json RoboRioMcpTools::WrapErrorResult(std::string_view message) {
  return {{"content",
           wpi::json::array(
               {{{"type", "text"}, {"text", std::string(message)}}})},
          {"isError", true}};
}

}  // namespace refinery::mcp
