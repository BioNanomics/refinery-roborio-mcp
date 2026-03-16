"""MCP tool definitions and implementations for reading robot state.

All tools are read-only — no robot control via MCP.
"""

import json


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
            topics[leaf_name] = f"[{nt_type.name}]"

    return json.dumps({"path": path, "subtables": subtables, "topics": topics})


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
