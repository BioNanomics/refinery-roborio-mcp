"""Tests for the MCP server HTTP handling and protocol routing.

Tests the server start/stop, HTTP endpoints, and JSON-RPC method dispatch
without requiring WPILib (mcp_tools is mocked).
"""

import json
import sys
import os
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock

# Add the package to path for testing without install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _post_mcp(port, payload):
    """Send a POST request to the MCP endpoint."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://localhost:{port}/mcp",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_server_start_stop():
    """Server starts on a port and stops cleanly."""
    from refinery_roborio_mcp.mcp_server import RoboRioMcpServer

    port = 18765
    RoboRioMcpServer.start(port)
    try:
        assert RoboRioMcpServer._instance is not None
        # Verify it responds
        resp = _post_mcp(port, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert resp["id"] == 1
        assert resp["result"] == {}
    finally:
        RoboRioMcpServer.stop()
    assert RoboRioMcpServer._instance is None


def test_initialize():
    """initialize method returns protocol version and server info."""
    from refinery_roborio_mcp.mcp_server import RoboRioMcpServer

    port = 18766
    RoboRioMcpServer.start(port)
    try:
        resp = _post_mcp(port, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        result = resp["result"]
        assert result["protocolVersion"] == "2025-03-26"
        assert result["serverInfo"]["name"] == "refinery-roborio-mcp"
        assert result["serverInfo"]["version"] == "0.0.3"
        assert "tools" in result["capabilities"]
    finally:
        RoboRioMcpServer.stop()


def test_method_not_found():
    """Unknown method returns JSON-RPC error -32601."""
    from refinery_roborio_mcp.mcp_server import RoboRioMcpServer

    port = 18767
    RoboRioMcpServer.start(port)
    try:
        resp = _post_mcp(port, {"jsonrpc": "2.0", "id": 1, "method": "bogus"})
        assert resp["error"]["code"] == -32601
        assert "bogus" in resp["error"]["message"]
    finally:
        RoboRioMcpServer.stop()


def test_missing_method():
    """Request without method field returns -32600."""
    from refinery_roborio_mcp.mcp_server import RoboRioMcpServer

    port = 18768
    RoboRioMcpServer.start(port)
    try:
        resp = _post_mcp(port, {"jsonrpc": "2.0", "id": 1})
        assert resp["error"]["code"] == -32600
    finally:
        RoboRioMcpServer.stop()


def test_tools_call_missing_name():
    """tools/call without a tool name returns -32602."""
    from refinery_roborio_mcp.mcp_server import RoboRioMcpServer

    port = 18769
    RoboRioMcpServer.start(port)
    try:
        resp = _post_mcp(port, {
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {},
        })
        assert resp["error"]["code"] == -32602
    finally:
        RoboRioMcpServer.stop()


def test_notifications_initialized():
    """notifications/initialized returns empty result."""
    from refinery_roborio_mcp.mcp_server import RoboRioMcpServer

    port = 18770
    RoboRioMcpServer.start(port)
    try:
        resp = _post_mcp(port, {
            "jsonrpc": "2.0", "id": 1,
            "method": "notifications/initialized",
        })
        assert resp["result"] == {}
    finally:
        RoboRioMcpServer.stop()


if __name__ == "__main__":
    test_server_start_stop()
    test_initialize()
    test_method_not_found()
    test_missing_method()
    test_tools_call_missing_name()
    test_notifications_initialized()
    print("All server tests passed!")
