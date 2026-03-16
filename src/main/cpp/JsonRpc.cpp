// Copyright (c) BioNanomics. All rights reserved.
// Licensed under the MIT License.

#include "refinery/mcp/JsonRpc.h"

#include <string>
#include <string_view>

namespace refinery::mcp {

std::string JsonRpc::ResultResponse(const wpi::json& id,
                                    const wpi::json& result) {
  wpi::json response = {
      {"jsonrpc", "2.0"}, {"id", id}, {"result", result}};
  return response.dump();
}

std::string JsonRpc::ErrorResponse(const wpi::json& id, int code,
                                   std::string_view message) {
  wpi::json response = {{"jsonrpc", "2.0"},
                         {"id", id},
                         {"error", {{"code", code}, {"message", std::string(message)}}}};
  return response.dump();
}

}  // namespace refinery::mcp
