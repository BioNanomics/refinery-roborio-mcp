# refinery-roborio-mcp

An embedded MCP (Model Context Protocol) server that runs inside FRC robot code on the roboRIO (and in simulation). Exposes robot status, match info, subsystem state, and NetworkTables browsing to AI assistants (GitHub Copilot, Claude, etc.) via HTTP JSON-RPC 2.0.


[Setup Short Video < 1min](https://www.instagram.com/reel/DV7w3rZDQpc/?igsh=ZWI2OGNlYnM2Njlj)

Supports both **Java** and **C++** robot projects.

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

### Java

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

### C++

In your `Robot.cpp` `RobotInit()`:

```cpp
#include <refinery/mcp/RoboRioMcpServer.h>

void Robot::RobotInit() {
    // ... existing init code ...
    refinery::mcp::RoboRioMcpServer::Start();        // default port 8765
    // refinery::mcp::RoboRioMcpServer::Start(9000); // or custom port
}
```

## MCP Client Configuration

### VS Code (GitHub Copilot)

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "roborio-mcp-sim": {
      "type": "http",
      "url": "http://localhost:8765/mcp"
    },
    "roborio-mcp": {
      "type": "http",
      "url": "http://10.TE.AM.2:8765/mcp"
    }
  }
}
```

Replace `10.TE.AM.2` with your team's roboRIO IP (e.g., `10.99.99.2` for team 9999).

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "roborio-mcp-sim": {
      "url": "http://localhost:8765/mcp"
    },
    "roborio-mcp": {
      "url": "http://10.TE.AM.2:8765/mcp"
    }
  }
}
```

Replace `10.TE.AM.2` with your team's roboRIO IP (e.g., `10.99.99.2` for team 9999).

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

### Java
- **Zero external dependencies** — uses a lightweight built-in JSON implementation (no Gson/Jackson)
- **WPILib is `compileOnly`** — the consuming robot project provides WPILib at runtime
- **2-thread HTTP server** — roboRIO-friendly resource usage via `com.sun.net.httpserver`

### C++
- **Uses `wpi::json`** (nlohmann JSON bundled with WPILib) — no custom JSON parser needed
- **POSIX sockets** for HTTP — zero external dependencies
- **2-worker thread pool** with a dedicated accept thread — roboRIO-friendly resource usage
- **Distributed as source** — headers + sources compiled by the consuming robot project

### Common
- **MCP protocol version:** `2025-03-26`
- **Transport:** Streamable HTTP on port 8765
- **All tools are read-only** — no robot control via MCP
- **7 tools** exposing robot status, battery, match info, stats, connections, subsystems, and NetworkTables

## License

MIT
