// Copyright (c) BioNanomics. All rights reserved.
// Licensed under the MIT License.

#pragma once

#include <string>

#include <wpi/json.h>

namespace refinery::mcp {

/**
 * JSON-RPC 2.0 response builder for MCP protocol.
 */
class JsonRpc {
 public:
  JsonRpc() = delete;

  /**
   * Build a JSON-RPC 2.0 success response.
   * @param id  Request id (number, string, or null).
   * @param result  Result payload.
   * @return Serialized JSON string.
   */
  static std::string ResultResponse(const wpi::json& id,
                                    const wpi::json& result);

  /**
   * Build a JSON-RPC 2.0 error response.
   * @param id  Request id (number, string, or null).
   * @param code  JSON-RPC error code.
   * @param message  Human-readable error message.
   * @return Serialized JSON string.
   */
  static std::string ErrorResponse(const wpi::json& id, int code,
                                   std::string_view message);
};

}  // namespace refinery::mcp
