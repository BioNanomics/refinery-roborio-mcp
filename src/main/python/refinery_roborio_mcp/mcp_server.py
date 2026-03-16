"""Embedded MCP server for FRC robots.

Exposes robot state via JSON-RPC 2.0 over HTTP (Streamable HTTP transport).
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from . import json_rpc
from .mcp_tools import RoboRioMcpTools

SERVER_NAME = "refinery-roborio-mcp"
SERVER_VERSION = "0.0.3"
MCP_PROTOCOL_VERSION = "2025-03-26"
DEFAULT_PORT = 8765


class _McpRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for the /mcp endpoint."""

    def do_POST(self):
        if self.path != "/mcp":
            self._send_error(404, "Not Found")
            return
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            request = json.loads(body)
            method = request.get("method")
            id = request.get("id")
            params = request.get("params", {})

            if method is None:
                response = json_rpc.error_response(id, -32600, "Invalid Request: missing method")
            else:
                response = _handle_method(method, params, id)

            self._send_json(response)
        except Exception as e:
            error_resp = json_rpc.error_response(None, -32700, f"Parse error: {e}")
            self._send_json(error_resp)

    def do_OPTIONS(self):
        if self.path != "/mcp":
            self._send_error(404, "Not Found")
            return
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, json_str):
        data = json_str.encode("utf-8")
        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, code, message):
        data = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Suppress default stderr logging
        pass


def _handle_method(method, params, id):
    """Route JSON-RPC methods to handlers."""
    if method == "initialize":
        return _handle_initialize(id)
    elif method == "notifications/initialized":
        return json_rpc.result_response(id, {})
    elif method == "tools/list":
        return _handle_tools_list(id)
    elif method == "tools/call":
        return _handle_tools_call(params, id)
    elif method == "ping":
        return json_rpc.result_response(id, {})
    else:
        return json_rpc.error_response(id, -32601, f"Method not found: {method}")


def _handle_initialize(id):
    result = {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }
    return json_rpc.result_response(id, result)


def _handle_tools_list(id):
    tools = RoboRioMcpTools.get_tool_definitions()
    return json_rpc.result_response(id, {"tools": tools})


def _handle_tools_call(params, id):
    if params is None:
        return json_rpc.error_response(id, -32602, "Invalid params: missing params")

    tool_name = params.get("name")
    if tool_name is None:
        return json_rpc.error_response(id, -32602, "Invalid params: missing tool name")

    tool_args = params.get("arguments", {})

    try:
        tool_result = RoboRioMcpTools.call_tool(tool_name, tool_args)
        return json_rpc.result_response(id, tool_result)
    except Exception as e:
        return json_rpc.error_response(id, -32603, f"Tool execution error: {e}")


class RoboRioMcpServer:
    """Embedded MCP server for FRC robots running RobotPy.

    Usage::

        from refinery_roborio_mcp import RoboRioMcpServer
        RoboRioMcpServer.start()       # default port 8765
        RoboRioMcpServer.start(9000)    # custom port
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, port):
        self._port = port
        self._server = HTTPServer(("", port), _McpRequestHandler)
        self._thread = None

    @staticmethod
    def start(port=DEFAULT_PORT):
        """Start the MCP server on the specified port (default 8765)."""
        with RoboRioMcpServer._lock:
            if RoboRioMcpServer._instance is not None:
                print(f"[MCP] Server already running on port {RoboRioMcpServer._instance._port}")
                return
            try:
                instance = RoboRioMcpServer(port)
                instance._thread = threading.Thread(
                    target=instance._server.serve_forever,
                    daemon=True,
                )
                instance._thread.start()
                RoboRioMcpServer._instance = instance
                print(f"[MCP] Server started on port {port}")
            except OSError as e:
                print(f"[MCP] Failed to start server: {e}")

    @staticmethod
    def stop():
        """Stop the MCP server if running."""
        with RoboRioMcpServer._lock:
            if RoboRioMcpServer._instance is not None:
                RoboRioMcpServer._instance._server.shutdown()
                RoboRioMcpServer._instance = None
                print("[MCP] Server stopped")
