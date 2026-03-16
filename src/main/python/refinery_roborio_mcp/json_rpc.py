"""JSON-RPC 2.0 response builder for MCP protocol."""

import json

JSONRPC_VERSION = "2.0"


def result_response(id, result):
    """Build a JSON-RPC 2.0 success response."""
    return json.dumps({
        "jsonrpc": JSONRPC_VERSION,
        "id": id,
        "result": result,
    })


def error_response(id, code, message):
    """Build a JSON-RPC 2.0 error response."""
    return json.dumps({
        "jsonrpc": JSONRPC_VERSION,
        "id": id,
        "error": {"code": code, "message": message},
    })
