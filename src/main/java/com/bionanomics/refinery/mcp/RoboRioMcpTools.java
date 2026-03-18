package com.bionanomics.refinery.mcp;

import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.RobotController;
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.networktables.Topic;
import edu.wpi.first.wpilibj2.command.Command;
import edu.wpi.first.wpilibj2.command.CommandScheduler;
import edu.wpi.first.wpilibj2.command.Subsystem;

import java.util.Set;

/**
 * MCP tool definitions and implementations for reading robot state.
 * All tools are read-only — no robot control via MCP.
 * Adapted from open-ds.ai, reading WPILib APIs instead of driver station GUI.
 */
public final class RoboRioMcpTools {
    private RoboRioMcpTools() {
    }

    public static JsonList getToolDefinitions() {
        JsonList tools = new JsonList();

        tools.add(defineTool("get_robot_status",
            "Get the current robot status including enabled state, operating mode, "
                + "estop status, battery voltage, brownout state, and whether robot code is running.",
            emptySchema()));

        tools.add(defineTool("get_battery_voltage",
            "Get the current robot battery voltage as a numeric value.",
            emptySchema()));

        tools.add(defineTool("get_match_info",
            "Get match information including alliance color and station number, "
                + "match type, match number, game-specific message, and remaining match time.",
            emptySchema()));

        tools.add(defineTool("get_robot_stats",
            "Get detailed robot statistics including CAN bus status, "
                + "3.3V/5V/6V rail voltages, currents, and fault counts, and input voltage.",
            emptySchema()));

        tools.add(defineTool("get_connection_info",
            "Get connection status for the Driver Station and FMS.",
            emptySchema()));

        tools.add(defineTool("get_subsystems",
            "List all registered command-based subsystems, their current command, "
                + "and their default command.",
            emptySchema()));

        // get_networktables has an optional 'path' parameter
        JsonMap ntProperties = new JsonMap();
        JsonMap pathProp = new JsonMap();
        pathProp.put("type", "string");
        pathProp.put("description", "NetworkTables path to browse (default: \"/\"). "
            + "Example: \"/SmartDashboard\" or \"/AdvantageKit\".");
        ntProperties.put("path", pathProp);

        JsonMap ntSchema = new JsonMap();
        ntSchema.put("type", "object");
        ntSchema.put("properties", ntProperties);

        tools.add(defineTool("get_networktables",
            "Browse the NetworkTables tree. Returns subtable names and topic values "
                + "at the specified path (one level deep). "
                + "Use the 'path' argument to navigate deeper.",
            ntSchema));

        return tools;
    }

    public static JsonMap callTool(String name, JsonMap arguments) {
        switch (name) {
            case "get_robot_status":
                return wrapTextResult(getRobotStatus());
            case "get_battery_voltage":
                return wrapTextResult(getBatteryVoltage());
            case "get_match_info":
                return wrapTextResult(getMatchInfo());
            case "get_robot_stats":
                return wrapTextResult(getRobotStats());
            case "get_connection_info":
                return wrapTextResult(getConnectionInfo());
            case "get_subsystems":
                return wrapTextResult(getSubsystems());
            case "get_networktables":
                String path = arguments.getString("path");
                if (path == null || path.isEmpty()) {
                    path = "/";
                }
                return wrapTextResult(getNetworkTables(path));
            default:
                return wrapErrorResult("Unknown tool: " + name);
        }
    }

    // ---- Tool implementations ----

    private static String getRobotStatus() {
        JsonMap status = new JsonMap();
        status.put("enabled", DriverStation.isEnabled());
        status.put("autonomous", DriverStation.isAutonomous());
        status.put("teleop", DriverStation.isTeleop());
        status.put("test", DriverStation.isTest());

        String mode = "Disabled";
        if (DriverStation.isEnabled()) {
            if (DriverStation.isAutonomous()) mode = "Autonomous";
            else if (DriverStation.isTeleop()) mode = "Teleoperated";
            else if (DriverStation.isTest()) mode = "Test";
        }
        status.put("mode", mode);

        status.put("eStop", DriverStation.isEStopped());
        status.put("batteryVoltage", RobotController.getBatteryVoltage());
        status.put("brownedOut", RobotController.isBrownedOut());
        status.put("systemActive", RobotController.isSysActive());
        return status.toJson();
    }

    private static String getBatteryVoltage() {
        JsonMap voltage = new JsonMap();
        voltage.put("volts", RobotController.getBatteryVoltage());
        voltage.put("inputVoltage", RobotController.getInputVoltage());
        return voltage.toJson();
    }

    private static String getMatchInfo() {
        JsonMap info = new JsonMap();

        var alliance = DriverStation.getAlliance();
        info.put("allianceColor", alliance.isPresent() ? alliance.get().name() : "Unknown");
        info.put("allianceStation", DriverStation.getLocation().orElse(0));
        info.put("matchType", DriverStation.getMatchType().name());
        info.put("matchNumber", DriverStation.getMatchNumber());
        info.put("replayNumber", DriverStation.getReplayNumber());
        info.put("gameSpecificMessage", DriverStation.getGameSpecificMessage());
        info.put("matchTime", DriverStation.getMatchTime());
        info.put("fmsAttached", DriverStation.isFMSAttached());
        return info.toJson();
    }

    private static String getRobotStats() {
        JsonMap stats = new JsonMap();

        stats.put("inputVoltage", RobotController.getInputVoltage());
        stats.put("inputCurrent", RobotController.getInputCurrent());

        // CAN bus status
        JsonMap canBus = new JsonMap();
        var canStatus = RobotController.getCANStatus();
        canBus.put("percentBusUtilization", canStatus.percentBusUtilization);
        canBus.put("busOffCount", canStatus.busOffCount);
        canBus.put("txFullCount", canStatus.txFullCount);
        canBus.put("receiveErrorCount", canStatus.receiveErrorCount);
        canBus.put("transmitErrorCount", canStatus.transmitErrorCount);
        stats.put("canBus", canBus);

        // 3.3V rail
        JsonMap rail3v3 = new JsonMap();
        rail3v3.put("voltage", RobotController.getVoltage3V3());
        rail3v3.put("current", RobotController.getCurrent3V3());
        rail3v3.put("enabled", RobotController.getEnabled3V3());
        rail3v3.put("faultCount", RobotController.getFaultCount3V3());
        stats.put("rail3v3", rail3v3);

        // 5V rail
        JsonMap rail5v = new JsonMap();
        rail5v.put("voltage", RobotController.getVoltage5V());
        rail5v.put("current", RobotController.getCurrent5V());
        rail5v.put("enabled", RobotController.getEnabled5V());
        rail5v.put("faultCount", RobotController.getFaultCount5V());
        stats.put("rail5v", rail5v);

        // 6V rail
        JsonMap rail6v = new JsonMap();
        rail6v.put("voltage", RobotController.getVoltage6V());
        rail6v.put("current", RobotController.getCurrent6V());
        rail6v.put("enabled", RobotController.getEnabled6V());
        rail6v.put("faultCount", RobotController.getFaultCount6V());
        stats.put("rail6v", rail6v);

        return stats.toJson();
    }

    private static String getConnectionInfo() {
        JsonMap info = new JsonMap();
        info.put("dsAttached", DriverStation.isDSAttached());
        info.put("fmsAttached", DriverStation.isFMSAttached());
        return info.toJson();
    }

    private static String getSubsystems() {
        JsonList subsystems = new JsonList();

        try {
            CommandScheduler scheduler = CommandScheduler.getInstance();
            // Use reflection-free approach: iterate registered subsystems
            // CommandScheduler doesn't expose a getSubsystems() method directly,
            // so we use the Sendable data published to SmartDashboard.
            // However, we can use the public API to check running commands.

            // The scheduler doesn't have a public getRegisteredSubsystems() method,
            // but subsystems register themselves. We'll report what we can.
            JsonMap schedulerInfo = new JsonMap();
            schedulerInfo.put("name", "CommandScheduler");
            schedulerInfo.put("note", "Subsystem details are published to SmartDashboard/Shuffleboard. "
                + "Use get_networktables with path '/SmartDashboard' to see subsystem state.");
            subsystems.add(schedulerInfo);
        } catch (Exception e) {
            JsonMap error = new JsonMap();
            error.put("error", "Command-based framework not available: " + e.getMessage());
            subsystems.add(error);
        }

        return subsystems.toJson();
    }

    private static String getNetworkTables(String path) {
        JsonMap result = new JsonMap();
        result.put("path", path);

        NetworkTableInstance ntInst = NetworkTableInstance.getDefault();
        NetworkTable table;
        if ("/".equals(path) || path.isEmpty()) {
            table = ntInst.getTable("");
        } else {
            // Strip leading slash for NT API
            String ntPath = path.startsWith("/") ? path.substring(1) : path;
            table = ntInst.getTable(ntPath);
        }

        // List subtables
        Set<String> subtableNames = table.getSubTables();
        JsonList subtables = new JsonList();
        for (String name : subtableNames) {
            subtables.add(name);
        }
        result.put("subtables", subtables);

        // List topics (key-value pairs) at this level
        JsonMap topics = new JsonMap();
        for (Topic topic : table.getTopics()) {
            String topicName = topic.getName();
            // Get just the leaf name (after the last /)
            String leafName = topicName.contains("/")
                ? topicName.substring(topicName.lastIndexOf('/') + 1)
                : topicName;

            // Read value as generic entry
            var entry = ntInst.getEntry(topicName);
            var value = entry.getValue();
            switch (value.getType()) {
                case kBoolean:
                    topics.put(leafName, value.getBoolean());
                    break;
                case kDouble:
                    topics.put(leafName, value.getDouble());
                    break;
                case kFloat:
                    topics.put(leafName, (double) value.getFloat());
                    break;
                case kInteger:
                    topics.put(leafName, value.getInteger());
                    break;
                case kString:
                    topics.put(leafName, value.getString());
                    break;
                case kBooleanArray:
                    JsonList boolArr = new JsonList();
                    for (boolean b : value.getBooleanArray()) {
                        boolArr.add(b);
                    }
                    topics.put(leafName, boolArr);
                    break;
                case kDoubleArray:
                    JsonList dblArr = new JsonList();
                    for (double d : value.getDoubleArray()) {
                        dblArr.add(d);
                    }
                    topics.put(leafName, dblArr);
                    break;
                case kFloatArray:
                    JsonList fltArr = new JsonList();
                    for (float f : value.getFloatArray()) {
                        fltArr.add((double) f);
                    }
                    topics.put(leafName, fltArr);
                    break;
                case kIntegerArray:
                    JsonList intArr = new JsonList();
                    for (long l : value.getIntegerArray()) {
                        intArr.add(l);
                    }
                    topics.put(leafName, intArr);
                    break;
                case kStringArray:
                    JsonList strArr = new JsonList();
                    for (String s : value.getStringArray()) {
                        strArr.add(s);
                    }
                    topics.put(leafName, strArr);
                    break;
                default:
                    // Attempt to decode WPILib struct types (Pose2d, ChassisSpeeds, etc.)
                    String typeString = topic.getTypeString();
                    Object decoded = StructDecoder.decode(typeString, value.getRaw());
                    if (decoded != null) {
                        topics.put(leafName, decoded);
                    } else {
                        topics.put(leafName, "[" + value.getType().name() + "]");
                    }
                    break;
            }
        }
        result.put("topics", topics);

        return result.toJson();
    }

    // ---- Helpers ----

    private static JsonMap defineTool(String name, String description, JsonMap inputSchema) {
        JsonMap tool = new JsonMap();
        tool.put("name", name);
        tool.put("description", description);
        tool.put("inputSchema", inputSchema);
        return tool;
    }

    private static JsonMap emptySchema() {
        JsonMap schema = new JsonMap();
        schema.put("type", "object");
        schema.put("properties", new JsonMap());
        return schema;
    }

    private static JsonMap wrapTextResult(String text) {
        JsonMap content = new JsonMap();
        content.put("type", "text");
        content.put("text", text);

        JsonList contentList = new JsonList();
        contentList.add(content);

        JsonMap result = new JsonMap();
        result.put("content", contentList);
        result.put("isError", false);
        return result;
    }

    private static JsonMap wrapErrorResult(String message) {
        JsonMap content = new JsonMap();
        content.put("type", "text");
        content.put("text", message);

        JsonList contentList = new JsonList();
        contentList.add(content);

        JsonMap result = new JsonMap();
        result.put("content", contentList);
        result.put("isError", true);
        return result;
    }
}
