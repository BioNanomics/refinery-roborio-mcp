// Copyright (c) BioNanomics. All rights reserved.
// Licensed under the MIT License.

#pragma once

#include <atomic>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

#include <wpi/json.h>

namespace refinery::mcp {

/**
 * Embedded MCP server for FRC robots.
 * Exposes robot state via JSON-RPC 2.0 over HTTP (Streamable HTTP transport).
 */
class RoboRioMcpServer {
 public:
  static constexpr const char* kServerName = "refinery-roborio-mcp";
  static constexpr const char* kServerVersion = "0.0.3";
  static constexpr const char* kMcpProtocolVersion = "2025-03-26";
  static constexpr int kDefaultPort = 8765;

  RoboRioMcpServer(const RoboRioMcpServer&) = delete;
  RoboRioMcpServer& operator=(const RoboRioMcpServer&) = delete;

  /** Start the MCP server on the default port (8765). */
  static void Start();

  /** Start the MCP server on the specified port. */
  static void Start(int port);

  /** Stop the MCP server if running. */
  static void Stop();

 private:
  explicit RoboRioMcpServer(int port);
  ~RoboRioMcpServer();

  void Run();
  void HandleClient(int clientFd);
  std::string HandlePost(std::string_view body);
  std::string HandleMethod(std::string_view method, const wpi::json& params,
                           const wpi::json& id);
  std::string HandleInitialize(const wpi::json& id);
  std::string HandleToolsList(const wpi::json& id);
  std::string HandleToolsCall(const wpi::json& params, const wpi::json& id);

  // Worker thread pool
  void WorkerLoop();
  void Enqueue(std::function<void()> task);

  int m_port;
  int m_serverFd = -1;
  std::atomic<bool> m_running{false};
  std::thread m_acceptThread;

  // Worker pool (2 threads)
  static constexpr int kWorkerCount = 2;
  std::vector<std::thread> m_workers;
  std::queue<std::function<void()>> m_taskQueue;
  std::mutex m_queueMutex;
  std::condition_variable m_queueCv;

  static RoboRioMcpServer* s_instance;
  static std::mutex s_instanceMutex;
};

}  // namespace refinery::mcp
