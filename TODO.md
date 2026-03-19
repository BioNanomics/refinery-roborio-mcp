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

## Phase 8: WPILib Struct Decoding
- [x] Java: `StructDecoder.java` — decode kRaw NT values into readable JSON
- [x] Java: Wire `StructDecoder` into `RoboRioMcpTools.getNetworkTables()` default case
- [x] C++: Add struct decoding to `RoboRioMcpTools::GetNetworkTables()` default case
  - Use `topic.GetTypeString()` to identify struct type (e.g. `"struct:Pose2d"`)
  - Use `value.GetRaw()` to get raw bytes
  - Decode little-endian IEEE 754 doubles via `std::memcpy` from raw byte spans
  - Support: Pose2d (24B), Pose3d (56B), Translation2d (16B), Translation3d (24B),
    Rotation2d (8B), Rotation3d (32B), Quaternion (32B), ChassisSpeeds (24B),
    SwerveModuleState (16B), SwerveModulePosition (16B), Transform2d (24B), Twist2d (24B)
  - Array types: detect `"struct:Pose2d[]"` suffix, decode N items from `raw.size() / structSize`
  - Return `wpi::json` objects with named fields (e.g. `{"translation":{"x":...,"y":...},"rotation":{"radians":...}}`)
- [x] Python: Add struct decoding to `mcp_tools._get_networktables()` else branch
  - Use `topic.getTypeString()` to identify struct type
  - Use `value.getRaw()` to get raw bytes
  - Decode with `struct.unpack_from('<d', raw, offset)` for each double field
  - Same type/size table as Java and C++
  - Array types: detect `[]` suffix, unpack `len(raw) // struct_size` items
  - Return plain dicts with named fields
- [x] Add CI parity test: all three languages return identical JSON structure for the same struct types

## Phase 9: Vision Support
- [x] Java: `get_vision_status` tool — reads all AdvantageKit `/RealOutputs/Vision/*` keys
  and SmartDashboard toggles in one call (cameras, coprocessors, seeding, detection, poses)
- [x] C++: `get_vision_status` tool — same output structure as Java
- [x] Python: `get_vision_status` tool — same output structure as Java
- [x] Bump SERVER_VERSION to 0.0.5 (Java)

## Future
- [ ] Publish to Maven repository for vendordep distribution
- [ ] AdvantageKit-specific tool for structured log browsing
- [ ] Recursive NetworkTables browsing option
- [ ] Resource/prompt support in MCP protocol
