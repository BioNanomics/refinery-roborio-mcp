"""MCP tool definitions and implementations for reading robot state.

All tools are read-only — no robot control via MCP.
"""

import json
import struct as _struct


class RoboRioMcpTools:
    """Static tool registry matching the Java/C++ implementations."""

    @staticmethod
    def get_tool_definitions():
        """Return the list of all MCP tool definitions."""
        tools = [
            _define_tool(
                "get_robot_status",
                "Get the current robot status including enabled state, operating mode, "
                "estop status, battery voltage, brownout state, and whether robot code is running.",
                _empty_schema(),
            ),
            _define_tool(
                "get_battery_voltage",
                "Get the current robot battery voltage as a numeric value.",
                _empty_schema(),
            ),
            _define_tool(
                "get_match_info",
                "Get match information including alliance color and station number, "
                "match type, match number, game-specific message, and remaining match time.",
                _empty_schema(),
            ),
            _define_tool(
                "get_robot_stats",
                "Get detailed robot statistics including CAN bus status, "
                "3.3V/5V/6V rail voltages, currents, and fault counts, and input voltage.",
                _empty_schema(),
            ),
            _define_tool(
                "get_connection_info",
                "Get connection status for the Driver Station and FMS.",
                _empty_schema(),
            ),
            _define_tool(
                "get_subsystems",
                "List all registered command-based subsystems, their current command, "
                "and their default command.",
                _empty_schema(),
            ),
            _define_tool(
                "get_networktables",
                "Browse the NetworkTables tree. Returns subtable names and topic values "
                "at the specified path (one level deep). "
                "Use the 'path' argument to navigate deeper.",
                {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                'NetworkTables path to browse (default: "/"). '
                                'Example: "/SmartDashboard" or "/AdvantageKit".'
                            ),
                        },
                    },
                },
            ),
        ]
        return tools

    @staticmethod
    def call_tool(name, arguments):
        """Dispatch a tool call by name and return the MCP result envelope."""
        handlers = {
            "get_robot_status": lambda: _wrap_text_result(_get_robot_status()),
            "get_battery_voltage": lambda: _wrap_text_result(_get_battery_voltage()),
            "get_match_info": lambda: _wrap_text_result(_get_match_info()),
            "get_robot_stats": lambda: _wrap_text_result(_get_robot_stats()),
            "get_connection_info": lambda: _wrap_text_result(_get_connection_info()),
            "get_subsystems": lambda: _wrap_text_result(_get_subsystems()),
            "get_networktables": lambda: _wrap_text_result(
                _get_networktables(arguments.get("path") or "/")
            ),
        }
        handler = handlers.get(name)
        if handler is None:
            return _wrap_error_result(f"Unknown tool: {name}")
        return handler()


# ---- Tool implementations ----


def _get_robot_status():
    import wpilib
    ds = wpilib.DriverStation
    rc = wpilib.RobotController

    mode = "Disabled"
    if ds.isEnabled():
        if ds.isAutonomous():
            mode = "Autonomous"
        elif ds.isTeleop():
            mode = "Teleoperated"
        elif ds.isTest():
            mode = "Test"

    return json.dumps({
        "enabled": ds.isEnabled(),
        "autonomous": ds.isAutonomous(),
        "teleop": ds.isTeleop(),
        "test": ds.isTest(),
        "mode": mode,
        "eStop": ds.isEStopped(),
        "batteryVoltage": rc.getBatteryVoltage(),
        "brownedOut": rc.isBrownedOut(),
        "systemActive": rc.isSysActive(),
    })


def _get_battery_voltage():
    import wpilib
    rc = wpilib.RobotController
    return json.dumps({
        "volts": rc.getBatteryVoltage(),
        "inputVoltage": rc.getInputVoltage(),
    })


def _get_match_info():
    import wpilib
    ds = wpilib.DriverStation

    alliance = ds.getAlliance()
    if alliance is not None:
        alliance_name = alliance.name
    else:
        alliance_name = "Unknown"

    location = ds.getLocation()
    station = location if location is not None else 0

    return json.dumps({
        "allianceColor": alliance_name,
        "allianceStation": station,
        "matchType": ds.getMatchType().name,
        "matchNumber": ds.getMatchNumber(),
        "replayNumber": ds.getReplayNumber(),
        "gameSpecificMessage": ds.getGameSpecificMessage(),
        "matchTime": ds.getMatchTime(),
        "fmsAttached": ds.isFMSAttached(),
    })


def _get_robot_stats():
    import wpilib
    rc = wpilib.RobotController
    can_status = rc.getCANStatus()

    return json.dumps({
        "inputVoltage": rc.getInputVoltage(),
        "inputCurrent": rc.getInputCurrent(),
        "canBus": {
            "percentBusUtilization": can_status.percentBusUtilization,
            "busOffCount": can_status.busOffCount,
            "txFullCount": can_status.txFullCount,
            "receiveErrorCount": can_status.receiveErrorCount,
            "transmitErrorCount": can_status.transmitErrorCount,
        },
        "rail3v3": {
            "voltage": rc.getVoltage3V3(),
            "current": rc.getCurrent3V3(),
            "enabled": rc.getEnabled3V3(),
            "faultCount": rc.getFaultCount3V3(),
        },
        "rail5v": {
            "voltage": rc.getVoltage5V(),
            "current": rc.getCurrent5V(),
            "enabled": rc.getEnabled5V(),
            "faultCount": rc.getFaultCount5V(),
        },
        "rail6v": {
            "voltage": rc.getVoltage6V(),
            "current": rc.getCurrent6V(),
            "enabled": rc.getEnabled6V(),
            "faultCount": rc.getFaultCount6V(),
        },
    })


def _get_connection_info():
    import wpilib
    ds = wpilib.DriverStation
    return json.dumps({
        "dsAttached": ds.isDSAttached(),
        "fmsAttached": ds.isFMSAttached(),
    })


def _get_subsystems():
    try:
        from commands2 import CommandScheduler
        _scheduler = CommandScheduler.getInstance()
        result = [
            {
                "name": "CommandScheduler",
                "note": (
                    "Subsystem details are published to SmartDashboard/Shuffleboard. "
                    "Use get_networktables with path '/SmartDashboard' to see subsystem state."
                ),
            }
        ]
    except Exception as e:
        result = [{"error": f"Command-based framework not available: {e}"}]

    return json.dumps(result)


def _get_networktables(path):
    import ntcore
    nt_inst = ntcore.NetworkTableInstance.getDefault()

    if path == "/" or path == "":
        table = nt_inst.getTable("")
    else:
        nt_path = path.lstrip("/")
        table = nt_inst.getTable(nt_path)

    subtables = sorted(table.getSubTables())

    topics = {}
    for topic in table.getTopics():
        topic_name = topic.getName()
        leaf_name = topic_name.rsplit("/", 1)[-1] if "/" in topic_name else topic_name

        entry = nt_inst.getEntry(topic_name)
        value = entry.getValue()
        nt_type = value.type()

        nt_types = ntcore.NetworkTableType
        if nt_type == nt_types.kBoolean:
            topics[leaf_name] = value.getBoolean()
        elif nt_type == nt_types.kDouble:
            topics[leaf_name] = value.getDouble()
        elif nt_type == nt_types.kFloat:
            topics[leaf_name] = float(value.getFloat())
        elif nt_type == nt_types.kInteger:
            topics[leaf_name] = value.getInteger()
        elif nt_type == nt_types.kString:
            topics[leaf_name] = value.getString()
        elif nt_type == nt_types.kBooleanArray:
            topics[leaf_name] = list(value.getBooleanArray())
        elif nt_type == nt_types.kDoubleArray:
            topics[leaf_name] = list(value.getDoubleArray())
        elif nt_type == nt_types.kFloatArray:
            topics[leaf_name] = [float(f) for f in value.getFloatArray()]
        elif nt_type == nt_types.kIntegerArray:
            topics[leaf_name] = list(value.getIntegerArray())
        elif nt_type == nt_types.kStringArray:
            topics[leaf_name] = list(value.getStringArray())
        else:
            # Attempt to decode WPILib struct types (Pose2d, ChassisSpeeds, etc.)
            type_str = topic.getTypeString()
            raw = value.getRaw()
            decoded = _decode_struct(type_str, raw)
            if decoded is not None:
                topics[leaf_name] = decoded
            else:
                topics[leaf_name] = f"[{nt_type.name}]"

    return json.dumps({"path": path, "subtables": subtables, "topics": topics})


# ---- Struct decoding ----

_STRUCT_SIZES = {
    "Rotation2d": 8,
    "Translation2d": 16,
    "Pose2d": 24,
    "Transform2d": 24,
    "Twist2d": 24,
    "ChassisSpeeds": 24,
    "SwerveModuleState": 16,
    "SwerveModulePosition": 16,
    "Quaternion": 32,
    "Rotation3d": 32,
    "Translation3d": 24,
    "Pose3d": 56,
}


def _read_double(raw, offset):
    return _struct.unpack_from("<d", raw, offset)[0]


def _decode_rotation2d(raw, off):
    return {"radians": _read_double(raw, off)}


def _decode_translation2d(raw, off):
    return {"x": _read_double(raw, off), "y": _read_double(raw, off + 8)}


def _decode_pose2d(raw, off):
    return {
        "translation": _decode_translation2d(raw, off),
        "rotation": _decode_rotation2d(raw, off + 16),
    }


def _decode_transform2d(raw, off):
    return {
        "translation": _decode_translation2d(raw, off),
        "rotation": _decode_rotation2d(raw, off + 16),
    }


def _decode_twist2d(raw, off):
    return {
        "dx": _read_double(raw, off),
        "dy": _read_double(raw, off + 8),
        "dtheta": _read_double(raw, off + 16),
    }


def _decode_chassis_speeds(raw, off):
    return {
        "vx": _read_double(raw, off),
        "vy": _read_double(raw, off + 8),
        "omega": _read_double(raw, off + 16),
    }


def _decode_swerve_module_state(raw, off):
    return {"speed": _read_double(raw, off), "angle": _decode_rotation2d(raw, off + 8)}


def _decode_swerve_module_position(raw, off):
    return {"distance": _read_double(raw, off), "angle": _decode_rotation2d(raw, off + 8)}


def _decode_quaternion(raw, off):
    return {
        "w": _read_double(raw, off),
        "x": _read_double(raw, off + 8),
        "y": _read_double(raw, off + 16),
        "z": _read_double(raw, off + 24),
    }


def _decode_rotation3d(raw, off):
    return {"quaternion": _decode_quaternion(raw, off)}


def _decode_translation3d(raw, off):
    return {
        "x": _read_double(raw, off),
        "y": _read_double(raw, off + 8),
        "z": _read_double(raw, off + 16),
    }


def _decode_pose3d(raw, off):
    return {
        "translation": _decode_translation3d(raw, off),
        "rotation": _decode_rotation3d(raw, off + 24),
    }


_STRUCT_DECODERS = {
    "Rotation2d": _decode_rotation2d,
    "Translation2d": _decode_translation2d,
    "Pose2d": _decode_pose2d,
    "Transform2d": _decode_transform2d,
    "Twist2d": _decode_twist2d,
    "ChassisSpeeds": _decode_chassis_speeds,
    "SwerveModuleState": _decode_swerve_module_state,
    "SwerveModulePosition": _decode_swerve_module_position,
    "Quaternion": _decode_quaternion,
    "Rotation3d": _decode_rotation3d,
    "Translation3d": _decode_translation3d,
    "Pose3d": _decode_pose3d,
}


def _decode_struct(type_string, raw):
    """Decode a WPILib struct type from raw NT bytes. Returns dict/list or None."""
    if not type_string or not raw:
        return None
    if not type_string.startswith("struct:"):
        return None

    struct_part = type_string[len("struct:"):]
    is_array = struct_part.endswith("[]")
    type_name = struct_part[:-2] if is_array else struct_part

    size = _STRUCT_SIZES.get(type_name)
    if size is None or len(raw) < size:
        return None

    decoder = _STRUCT_DECODERS.get(type_name)
    if decoder is None:
        return None

    if not is_array:
        return decoder(raw, 0)

    count = len(raw) // size
    return [decoder(raw, i * size) for i in range(count)]


# ---- Helpers ----


def _define_tool(name, description, input_schema):
    return {"name": name, "description": description, "inputSchema": input_schema}


def _empty_schema():
    return {"type": "object", "properties": {}}


def _wrap_text_result(text):
    return {
        "content": [{"type": "text", "text": text}],
        "isError": False,
    }


def _wrap_error_result(message):
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }
