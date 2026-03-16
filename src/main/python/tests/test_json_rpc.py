"""Tests for json_rpc module."""

import json
import sys
import os

# Add the package to path for testing without install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from refinery_roborio_mcp.json_rpc import result_response, error_response


def test_result_response():
    raw = result_response(1, {"key": "value"})
    parsed = json.loads(raw)
    assert parsed["jsonrpc"] == "2.0"
    assert parsed["id"] == 1
    assert parsed["result"] == {"key": "value"}
    assert "error" not in parsed


def test_result_response_with_null_id():
    raw = result_response(None, {})
    parsed = json.loads(raw)
    assert parsed["id"] is None
    assert parsed["result"] == {}


def test_error_response():
    raw = error_response(42, -32601, "Method not found")
    parsed = json.loads(raw)
    assert parsed["jsonrpc"] == "2.0"
    assert parsed["id"] == 42
    assert parsed["error"]["code"] == -32601
    assert parsed["error"]["message"] == "Method not found"
    assert "result" not in parsed


def test_error_response_with_null_id():
    raw = error_response(None, -32700, "Parse error")
    parsed = json.loads(raw)
    assert parsed["id"] is None
    assert parsed["error"]["code"] == -32700


if __name__ == "__main__":
    test_result_response()
    test_result_response_with_null_id()
    test_error_response()
    test_error_response_with_null_id()
    print("All json_rpc tests passed!")
