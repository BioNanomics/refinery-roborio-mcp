## Project Overview

This is a Java and C++ library providing an embedded MCP (Model Context Protocol) server for FRC robots running on the roboRIO. It exposes read-only robot state via HTTP JSON-RPC 2.0 on port 8765 with zero external dependencies.

**Stack**: Java 17 + C++17, WPILib 2026.x, Gradle, MCP protocol 2025-03-26

---

## Code Quality Principles

### DRY (Don't Repeat Yourself)
- Extract reusable functions — never duplicate code
- Single source of truth for each piece of knowledge
- Common patterns belong in utility classes (e.g., `JsonUtil`, `JsonRpc`)

### KISS (Keep It Simple, Stupid)
- Prefer the simplest solution that works
- No external dependencies unless absolutely necessary — this runs on a roboRIO with limited resources
- Self-documenting names; small, focused functions
- No over-engineering for hypothetical future needs

### Dead Code
- Delete unused code immediately
- Move significant dead code to `.attic/` with explanatory comments

---

## Java & roboRIO Conventions

### Resource Constraints
- **Minimal thread usage**: HTTP server uses a fixed 2-thread pool — keep it small
- **No reflection or heavy frameworks**: Hand-written JSON parser in Java, `wpi::json` in C++, no Gson/Jackson/regex
- **compileOnly WPILib deps**: WPILib APIs are provided at runtime by the robot project — never bundle them
- **C++ source distribution**: Headers + sources are zipped and compiled by the consuming project

### Static Design Pattern
- Utility and tool classes are entirely static (`JsonRpc`, `JsonParser`, `RoboRioMcpTools`)
- Server uses a singleton via `RoboRioMcpServer.start()` (Java) / `RoboRioMcpServer::Start()` (C++) — no public `getInstance()`
- WPILib APIs are accessed directly via static calls (`DriverStation`, `RobotController`, `NetworkTableInstance`)

### Error Handling
- Tool implementations catch exceptions and return `JsonRpc.errorResponse()`
- HTTP errors use `sendError(code, message)` with appropriate status codes
- Standard JSON-RPC error codes: `-32700` (parse), `-32601` (method not found), `-32602` (invalid params)

### Naming Conventions
- **Java classes**: PascalCase (`RoboRioMcpServer`, `JsonMap`)
- **Java methods/variables**: camelCase (`getRobotStatus()`, `batteryVoltage`)
- **C++ classes**: PascalCase in `refinery::mcp` namespace (`RoboRioMcpServer`, `JsonRpc`)
- **C++ methods**: PascalCase (`Start()`, `CallTool()`), private members `m_` prefixed
- **MCP tool names**: snake_case (`get_robot_status`, `get_battery_voltage`)
- **JSON properties**: camelCase (`allianceColor`, `busUtilization`)

---

## MCP Tool Conventions

### Tool Definition Pattern
- Each tool uses `defineTool(name, description, inputSchema)` in `RoboRioMcpTools`
- Input schemas follow JSON Schema object format; parameterless tools use `emptySchema()`
- All tools are **read-only and stateless** — never mutate robot state

### Response Format
- Tool results wrap in: `{ "content": [{ "type": "text", "text": "..." }], "isError": false }`
- Use `JsonRpc.wrapTextResult()` to produce consistent output
- Error responses: `{ "jsonrpc": "2.0", "id": <id>, "error": { "code": <code>, "message": "..." } }`

### JSON Data Structures
- **Java**: `JsonMap` uses `LinkedHashMap` to preserve insertion order in output; `JsonList` wraps `ArrayList`; `JsonUtil` handles serialization and string escaping
- **C++**: Uses `wpi::json` (nlohmann JSON) — no custom JSON infrastructure needed

---

## Version Alignment

- **WPILib version** in `build.gradle` must stay in sync with the consuming robot project's GradleRIO version
- **MCP protocol version** is explicitly tracked in `RoboRioMcpServer` (`2025-03-26`)
- **Vendordep JSON** (`vendordep/refinery-roborio-mcp.json`) must be updated on each release

---

## Documentation

- Use Mermaid diagrams for architecture/workflow documentation (not ASCII art)
- Use memorable names in diagrams (`Server`, `DriverStation` — not `A`, `B`)
- Keep docs DRY — reference other files instead of duplicating content
- JavaDoc on all public Java classes and methods
- Doxygen-style comments on all public C++ classes and methods

---

## Pull Request Philosophy

- **Smallest viable change** that fully solves the problem
- **Fewest files first** — start with the minimal set
- No sweeping edits; extract complexity into new functions/classes rather than modifying many areas
- Large refactors only when explicitly requested

### Code Quality Checklist
- [ ] No code duplication — extracted reusable functions?
- [ ] Simplest solution that works?
- [ ] Smallest viable change for PR?
- [ ] Self-documenting names?
- [ ] Functions small and focused?
- [ ] Dead code removed or archived?
- [ ] JavaDoc on public Java API?
- [ ] Doxygen comments on public C++ API?
- [ ] `./gradlew build` passes?
- [ ] Tests pass (when available)?
