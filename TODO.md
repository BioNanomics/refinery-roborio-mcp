# TODO — refinery-roborio-mcp

## Phase 1: Project Scaffold
- [x] Create project directory + git init
- [x] README.md + TODO.md
- [x] `build.gradle` (java-library + maven-publish, WPILib compileOnly)
- [x] `settings.gradle`
- [x] Wire into root project (includeBuild + dependency)

## Phase 2: JSON Infrastructure
- [x] `JsonMap.java` — JSON object representation
- [x] `JsonList.java` — JSON array representation
- [x] `JsonUtil.java` — JSON serialization/escaping
- [x] `JsonParser.java` — JSON request parsing
- [x] `JsonRpc.java` — JSON-RPC 2.0 response builder

## Phase 3: MCP Server Core
- [x] `RoboRioMcpServer.java` — HTTP server, JSON-RPC dispatch, start/stop API

## Phase 4: Tool Implementations
- [x] `RoboRioMcpTools.java` with 7 tools:
  - [x] `get_robot_status` (DriverStation + RobotController)
  - [x] `get_battery_voltage` (RobotController)
  - [x] `get_match_info` (DriverStation)
  - [x] `get_robot_stats` (RobotController)
  - [x] `get_connection_info` (DriverStation)
  - [x] `get_subsystems` (CommandScheduler)
  - [x] `get_networktables` (NetworkTableInstance)

## Phase 5: Documentation & Vendordep JSON
- [x] Vendordep JSON (`vendordep/refinery-roborio-mcp.json`)
- [x] README with installation, usage, tool reference

## Phase 6: C++ Port
- [x] `RoboRioMcpServer.h` / `.cpp` — POSIX socket HTTP server with 2-worker thread pool
- [x] `RoboRioMcpTools.h` / `.cpp` — All 7 tools using WPILib C++ APIs
- [x] `JsonRpc.h` / `.cpp` — JSON-RPC 2.0 response builders using `wpi::json`
- [x] `cppHeadersZip` / `cppSourcesZip` Gradle tasks + Maven publication
- [x] `cppDependencies` in vendordep JSON
- [x] README updated with C++ usage instructions

## Phase 7: Integration into Rufus
- [x] Add `RoboRioMcpServer.start()` to `Robot.java` constructor
- [x] Create `.vscode/mcp.json` with server entry

## Future
- [ ] Publish to Maven repository for vendordep distribution
- [ ] AdvantageKit-specific tool for structured log browsing
- [ ] Recursive NetworkTables browsing option
- [ ] Resource/prompt support in MCP protocol
