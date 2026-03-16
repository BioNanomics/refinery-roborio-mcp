package com.bionanomics.refinery.mcp;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Executors;

/**
 * Embedded MCP server for FRC robots.
 * Exposes robot state via JSON-RPC 2.0 over HTTP (Streamable HTTP transport).
 * Adapted from open-ds.ai.
 */
public class RoboRioMcpServer {
    public static final String SERVER_NAME = "refinery-roborio-mcp";
    public static final String SERVER_VERSION = "0.0.2";
    public static final String MCP_PROTOCOL_VERSION = "2025-03-26";
    public static final int DEFAULT_PORT = 8765;

    private static RoboRioMcpServer instance;

    private final HttpServer server;
    private final int port;

    private RoboRioMcpServer(int port) throws IOException {
        this.port = port;
        this.server = HttpServer.create(new InetSocketAddress(port), 0);
        this.server.setExecutor(Executors.newFixedThreadPool(2));
        this.server.createContext("/mcp", this::handleMcp);
    }

    /** Start the MCP server on the default port (8765). */
    public static void start() {
        start(DEFAULT_PORT);
    }

    /** Start the MCP server on the specified port. */
    public static void start(int port) {
        if (instance != null) {
            System.out.println("[MCP] Server already running on port " + instance.port);
            return;
        }
        try {
            instance = new RoboRioMcpServer(port);
            instance.server.start();
            System.out.println("[MCP] Server started on port " + port);
        } catch (IOException e) {
            System.err.println("[MCP] Failed to start server: " + e.getMessage());
        }
    }

    /** Stop the MCP server if running. */
    public static void stop() {
        if (instance != null) {
            instance.server.stop(0);
            instance = null;
            System.out.println("[MCP] Server stopped");
        }
    }

    private void handleMcp(HttpExchange exchange) throws IOException {
        if ("POST".equalsIgnoreCase(exchange.getRequestMethod())) {
            handlePost(exchange);
        } else if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
            setCorsHeaders(exchange);
            exchange.sendResponseHeaders(204, -1);
            exchange.close();
        } else {
            sendError(exchange, 405, "Method Not Allowed");
        }
    }

    private void handlePost(HttpExchange exchange) throws IOException {
        setCorsHeaders(exchange);
        String body = readBody(exchange.getRequestBody());

        try {
            JsonMap request = JsonParser.parseObject(body);
            String method = request.getString("method");
            Object id = request.get("id");
            JsonMap params = request.getMap("params");

            String response;
            if (method == null) {
                response = JsonRpc.errorResponse(id, -32600, "Invalid Request: missing method");
            } else {
                response = handleMethod(method, params, id);
            }

            sendJson(exchange, response);
        } catch (Exception e) {
            String errorResp = JsonRpc.errorResponse(null, -32700, "Parse error: " + e.getMessage());
            sendJson(exchange, errorResp);
        }
    }

    private String handleMethod(String method, JsonMap params, Object id) {
        switch (method) {
            case "initialize":
                return handleInitialize(id);
            case "notifications/initialized":
                return JsonRpc.resultResponse(id, new JsonMap());
            case "tools/list":
                return handleToolsList(id);
            case "tools/call":
                return handleToolsCall(params, id);
            case "ping":
                return JsonRpc.resultResponse(id, new JsonMap());
            default:
                return JsonRpc.errorResponse(id, -32601, "Method not found: " + method);
        }
    }

    private String handleInitialize(Object id) {
        JsonMap capabilities = new JsonMap();
        capabilities.put("tools", new JsonMap());

        JsonMap serverInfo = new JsonMap();
        serverInfo.put("name", SERVER_NAME);
        serverInfo.put("version", SERVER_VERSION);

        JsonMap result = new JsonMap();
        result.put("protocolVersion", MCP_PROTOCOL_VERSION);
        result.put("capabilities", capabilities);
        result.put("serverInfo", serverInfo);

        return JsonRpc.resultResponse(id, result);
    }

    private String handleToolsList(Object id) {
        JsonList tools = RoboRioMcpTools.getToolDefinitions();
        JsonMap result = new JsonMap();
        result.put("tools", tools);
        return JsonRpc.resultResponse(id, result);
    }

    private String handleToolsCall(JsonMap params, Object id) {
        if (params == null) {
            return JsonRpc.errorResponse(id, -32602, "Invalid params: missing params");
        }
        String toolName = params.getString("name");
        if (toolName == null) {
            return JsonRpc.errorResponse(id, -32602, "Invalid params: missing tool name");
        }
        JsonMap toolArgs = params.getMap("arguments");
        if (toolArgs == null) {
            toolArgs = new JsonMap();
        }

        try {
            JsonMap toolResult = RoboRioMcpTools.callTool(toolName, toolArgs);
            return JsonRpc.resultResponse(id, toolResult);
        } catch (Exception e) {
            return JsonRpc.errorResponse(id, -32603, "Tool execution error: " + e.getMessage());
        }
    }

    private void setCorsHeaders(HttpExchange exchange) {
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "POST, OPTIONS");
        exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type");
    }

    private void sendJson(HttpExchange exchange, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(200, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private void sendError(HttpExchange exchange, int code, String message) throws IOException {
        byte[] bytes = message.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(code, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private String readBody(InputStream is) throws IOException {
        byte[] buf = new byte[4096];
        StringBuilder sb = new StringBuilder();
        int bytesRead;
        while ((bytesRead = is.read(buf)) != -1) {
            sb.append(new String(buf, 0, bytesRead, StandardCharsets.UTF_8));
        }
        return sb.toString();
    }
}
