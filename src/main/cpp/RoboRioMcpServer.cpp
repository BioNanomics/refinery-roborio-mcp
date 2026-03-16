// Copyright (c) BioNanomics. All rights reserved.
// Licensed under the MIT License.

#include "refinery/mcp/RoboRioMcpServer.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <string_view>

#include "refinery/mcp/JsonRpc.h"
#include "refinery/mcp/RoboRioMcpTools.h"

namespace refinery::mcp {

RoboRioMcpServer* RoboRioMcpServer::s_instance = nullptr;
std::mutex RoboRioMcpServer::s_instanceMutex;

RoboRioMcpServer::RoboRioMcpServer(int port) : m_port(port) {}

RoboRioMcpServer::~RoboRioMcpServer() { Stop(); }

void RoboRioMcpServer::Start() { Start(kDefaultPort); }

void RoboRioMcpServer::Start(int port) {
  std::lock_guard lock(s_instanceMutex);
  if (s_instance) {
    std::cout << "[MCP] Server already running on port " << s_instance->m_port
              << std::endl;
    return;
  }

  auto* server = new RoboRioMcpServer(port);

  // Create socket
  server->m_serverFd = socket(AF_INET, SOCK_STREAM, 0);
  if (server->m_serverFd < 0) {
    std::cerr << "[MCP] Failed to create socket" << std::endl;
    delete server;
    return;
  }

  // Allow port reuse
  int opt = 1;
  setsockopt(server->m_serverFd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

  // Bind
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = INADDR_ANY;
  addr.sin_port = htons(static_cast<uint16_t>(port));

  if (bind(server->m_serverFd, reinterpret_cast<sockaddr*>(&addr),
           sizeof(addr)) < 0) {
    std::cerr << "[MCP] Failed to bind to port " << port << std::endl;
    close(server->m_serverFd);
    delete server;
    return;
  }

  if (listen(server->m_serverFd, 8) < 0) {
    std::cerr << "[MCP] Failed to listen" << std::endl;
    close(server->m_serverFd);
    delete server;
    return;
  }

  server->m_running = true;

  // Start worker threads
  for (int i = 0; i < kWorkerCount; ++i) {
    server->m_workers.emplace_back(&RoboRioMcpServer::WorkerLoop, server);
  }

  // Start accept thread
  server->m_acceptThread = std::thread(&RoboRioMcpServer::Run, server);

  s_instance = server;
  std::cout << "[MCP] Server started on port " << port << std::endl;
}

void RoboRioMcpServer::Stop() {
  std::lock_guard lock(s_instanceMutex);
  if (!s_instance) {
    return;
  }

  s_instance->m_running = false;

  // Close server socket to unblock accept()
  if (s_instance->m_serverFd >= 0) {
    close(s_instance->m_serverFd);
    s_instance->m_serverFd = -1;
  }

  // Wake up workers
  s_instance->m_queueCv.notify_all();

  if (s_instance->m_acceptThread.joinable()) {
    s_instance->m_acceptThread.join();
  }
  for (auto& w : s_instance->m_workers) {
    if (w.joinable()) {
      w.join();
    }
  }

  delete s_instance;
  s_instance = nullptr;
  std::cout << "[MCP] Server stopped" << std::endl;
}

void RoboRioMcpServer::Run() {
  while (m_running) {
    int clientFd = accept(m_serverFd, nullptr, nullptr);
    if (clientFd < 0) {
      break;  // Server socket closed or error
    }
    Enqueue([this, clientFd] { HandleClient(clientFd); });
  }
}

void RoboRioMcpServer::WorkerLoop() {
  while (true) {
    std::function<void()> task;
    {
      std::unique_lock lock(m_queueMutex);
      m_queueCv.wait(lock, [this] { return !m_running || !m_taskQueue.empty(); });
      if (!m_running && m_taskQueue.empty()) {
        return;
      }
      task = std::move(m_taskQueue.front());
      m_taskQueue.pop();
    }
    task();
  }
}

void RoboRioMcpServer::Enqueue(std::function<void()> task) {
  {
    std::lock_guard lock(m_queueMutex);
    m_taskQueue.push(std::move(task));
  }
  m_queueCv.notify_one();
}

void RoboRioMcpServer::HandleClient(int clientFd) {
  // Read request (up to 8KB)
  char buf[8192];
  std::string request;
  ssize_t n;
  while ((n = read(clientFd, buf, sizeof(buf))) > 0) {
    request.append(buf, static_cast<size_t>(n));
    // Check if we have full headers
    auto headerEnd = request.find("\r\n\r\n");
    if (headerEnd != std::string::npos) {
      // Check for Content-Length
      std::string lowerReq = request;
      for (auto& c : lowerReq) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
      }
      auto clPos = lowerReq.find("content-length:");
      if (clPos != std::string::npos) {
        size_t valStart = clPos + 15;
        while (valStart < lowerReq.size() && lowerReq[valStart] == ' ') {
          ++valStart;
        }
        int contentLen = std::atoi(lowerReq.c_str() + valStart);
        size_t totalNeeded = headerEnd + 4 + static_cast<size_t>(contentLen);
        if (request.size() >= totalNeeded) {
          break;
        }
      } else {
        break;  // No body expected
      }
    }
  }

  if (request.empty()) {
    close(clientFd);
    return;
  }

  // Parse request line
  auto firstLine = request.substr(0, request.find("\r\n"));
  std::string method;
  {
    auto spacePos = firstLine.find(' ');
    if (spacePos != std::string::npos) {
      method = firstLine.substr(0, spacePos);
    }
  }

  std::string responseBody;
  std::string statusLine;
  std::string extraHeaders;

  // CORS headers for all responses
  std::string corsHeaders =
      "Access-Control-Allow-Origin: *\r\n"
      "Access-Control-Allow-Methods: POST, OPTIONS\r\n"
      "Access-Control-Allow-Headers: Content-Type\r\n";

  if (method == "POST") {
    auto bodyStart = request.find("\r\n\r\n");
    std::string body;
    if (bodyStart != std::string::npos) {
      body = request.substr(bodyStart + 4);
    }
    responseBody = HandlePost(body);
    statusLine = "HTTP/1.1 200 OK\r\n";
    extraHeaders = "Content-Type: application/json\r\n";
  } else if (method == "OPTIONS") {
    statusLine = "HTTP/1.1 204 No Content\r\n";
    std::string response = statusLine + corsHeaders + "\r\n";
    write(clientFd, response.c_str(), response.size());
    close(clientFd);
    return;
  } else {
    responseBody = "Method Not Allowed";
    statusLine = "HTTP/1.1 405 Method Not Allowed\r\n";
  }

  // Build and send response
  std::ostringstream resp;
  resp << statusLine;
  resp << corsHeaders;
  resp << extraHeaders;
  resp << "Content-Length: " << responseBody.size() << "\r\n";
  resp << "Connection: close\r\n";
  resp << "\r\n";
  resp << responseBody;

  std::string respStr = resp.str();
  write(clientFd, respStr.c_str(), respStr.size());
  close(clientFd);
}

std::string RoboRioMcpServer::HandlePost(std::string_view body) {
  try {
    auto request = wpi::json::parse(body);

    auto methodIt = request.find("method");
    auto idIt = request.find("id");

    wpi::json id = (idIt != request.end()) ? *idIt : wpi::json{};
    wpi::json params =
        request.contains("params") ? request["params"] : wpi::json::object();

    if (methodIt == request.end() || !methodIt->is_string()) {
      return JsonRpc::ErrorResponse(id, -32600,
                                    "Invalid Request: missing method");
    }

    return HandleMethod(methodIt->get<std::string>(), params, id);
  } catch (const std::exception& e) {
    return JsonRpc::ErrorResponse(wpi::json{}, -32700,
                                  std::string("Parse error: ") + e.what());
  }
}

std::string RoboRioMcpServer::HandleMethod(std::string_view method,
                                           const wpi::json& params,
                                           const wpi::json& id) {
  if (method == "initialize") {
    return HandleInitialize(id);
  } else if (method == "notifications/initialized") {
    return JsonRpc::ResultResponse(id, wpi::json::object());
  } else if (method == "tools/list") {
    return HandleToolsList(id);
  } else if (method == "tools/call") {
    return HandleToolsCall(params, id);
  } else if (method == "ping") {
    return JsonRpc::ResultResponse(id, wpi::json::object());
  } else {
    return JsonRpc::ErrorResponse(
        id, -32601, std::string("Method not found: ") + std::string(method));
  }
}

std::string RoboRioMcpServer::HandleInitialize(const wpi::json& id) {
  wpi::json result = {
      {"protocolVersion", kMcpProtocolVersion},
      {"capabilities", {{"tools", wpi::json::object()}}},
      {"serverInfo", {{"name", kServerName}, {"version", kServerVersion}}}};
  return JsonRpc::ResultResponse(id, result);
}

std::string RoboRioMcpServer::HandleToolsList(const wpi::json& id) {
  wpi::json result = {{"tools", RoboRioMcpTools::GetToolDefinitions()}};
  return JsonRpc::ResultResponse(id, result);
}

std::string RoboRioMcpServer::HandleToolsCall(const wpi::json& params,
                                              const wpi::json& id) {
  if (params.is_null() || !params.is_object()) {
    return JsonRpc::ErrorResponse(id, -32602,
                                  "Invalid params: missing params");
  }
  if (!params.contains("name") || !params["name"].is_string()) {
    return JsonRpc::ErrorResponse(id, -32602,
                                  "Invalid params: missing tool name");
  }

  std::string toolName = params["name"].get<std::string>();
  wpi::json toolArgs = params.contains("arguments")
                           ? params["arguments"]
                           : wpi::json::object();

  try {
    wpi::json toolResult = RoboRioMcpTools::CallTool(toolName, toolArgs);
    return JsonRpc::ResultResponse(id, toolResult);
  } catch (const std::exception& e) {
    return JsonRpc::ErrorResponse(
        id, -32603,
        std::string("Tool execution error: ") + e.what());
  }
}

}  // namespace refinery::mcp
