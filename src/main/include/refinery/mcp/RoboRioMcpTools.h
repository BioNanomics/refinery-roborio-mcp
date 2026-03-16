// Copyright (c) BioNanomics. All rights reserved.
// Licensed under the MIT License.

#pragma once

#include <string>

#include <wpi/json.h>

namespace refinery::mcp {

/**
 * MCP tool definitions and implementations for reading robot state.
 * All tools are read-only — no robot control via MCP.
 */
class RoboRioMcpTools {
 public:
  RoboRioMcpTools() = delete;

  /**
   * Get all tool definitions (name, description, inputSchema).
   * @return JSON array of tool objects.
   */
  static wpi::json GetToolDefinitions();

  /**
   * Execute a tool by name.
   * @param name  Tool name (snake_case).
   * @param arguments  Tool arguments object.
   * @return MCP tool result with content array and isError flag.
   */
  static wpi::json CallTool(std::string_view name,
                            const wpi::json& arguments);

 private:
  static wpi::json DefineTool(std::string_view name,
                               std::string_view description,
                               const wpi::json& inputSchema);
  static wpi::json EmptySchema();
  static wpi::json WrapTextResult(std::string_view text);
  static wpi::json WrapErrorResult(std::string_view message);

  // Tool implementations
  static std::string GetRobotStatus();
  static std::string GetBatteryVoltage();
  static std::string GetMatchInfo();
  static std::string GetRobotStats();
  static std::string GetConnectionInfo();
  static std::string GetSubsystems();
  static std::string GetNetworkTables(std::string_view path);
};

}  // namespace refinery::mcp
