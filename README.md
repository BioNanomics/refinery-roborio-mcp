# refinery-roborio-mcp

An embedded MCP (Model Context Protocol) server that runs inside FRC robot code on the roboRIO (and in simulation). Exposes robot status, match info, subsystem state, and NetworkTables browsing to AI assistants (GitHub Copilot, Claude, etc.) via HTTP JSON-RPC 2.0.

Adapted from [open-ds.ai](https://github.com/horner/open-ds.ai)'s MCP server, but reading directly from WPILib APIs (`DriverStation`, `RobotController`, `CommandScheduler`, `NetworkTables`) rather than from a driver station GUI.

## Installation

### Composite Build (for development)

In your robot project's `settings.gradle`:

```gradle
includeBuild 'refinery-roborio-mcp'
```

In your `build.gradle` dependencies:

```gradle
implementation 'com.bionanomics.refinery:refinery-roborio-mcp'
```

### Vendordep (for distribution)

> *Coming soon* — once published to a Maven repository, teams will paste a vendordep JSON URL into their project.

## Usage

In your `Robot.java` `robotInit()`:

```java
import com.bionanomics.refinery.mcp.RoboRioMcpServer;

@Override
public void robotInit() {
    // ... existing init code ...
    RoboRioMcpServer.start();        // default port 8765
    // RoboRioMcpServer.start(9000); // or custom port
}
```

## MCP Client Configuration

### VS Code (GitHub Copilot)

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "roborio": {
      "type": "http",
      "url": "http://localhost:8765/mcp"
    }
  }
}
```

For a real robot, replace `localhost` with `10.xx.yy.2` (your team's roboRIO IP).

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "roborio": {
      "url": "http://localhost:8765/mcp"
    }
  }
}
```

## Available Tools

All tools are **read-only** — no robot control via MCP.

| Tool | Description |
|------|-------------|
| `get_robot_status` | Enabled state, operating mode, estop, battery voltage, brownout, code status |
| `get_battery_voltage` | Battery voltage as a double |
| `get_match_info` | Alliance color/station, match type/number, game message, match time |
| `get_robot_stats` | CAN bus status, 3.3V/5V/6V rail voltages/currents/faults, input voltage |
| `get_connection_info` | Driver Station connected, FMS connected |
| `get_subsystems` | Registered subsystems + their current/default commands |
| `get_networktables` | Browse NetworkTables tree (accepts optional `path` argument, default `/`) |

## Architecture

- **Zero external dependencies** — uses a lightweight built-in JSON implementation (no Gson/Jackson)
- **WPILib is `compileOnly`** — the consuming robot project provides WPILib at runtime
- **2-thread HTTP server** — roboRIO-friendly resource usage
- **MCP protocol version:** `2025-03-26`
- **Transport:** Streamable HTTP on port 8765

## License

MIT
