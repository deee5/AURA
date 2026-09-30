"""
AURA MCP Server — Full-featured Model Context Protocol 2024-11-05 implementation.
Supports stdio transport, HTTP/SSE transport, tool execution, resource reading, and prompt dispatch.
"""

from __future__ import annotations
import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional

from automation.mcp.schemas import (
    MCP_PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    JSONRPCErrorCodes,
)
from automation.mcp.tools import ALL_TOOLS, get_tool
from automation.mcp.resources import get_all_resources, read_resource
from automation.mcp.prompts import ALL_PROMPTS, get_prompt


class MCPServer:
    """Production-grade Model Context Protocol (MCP) Server for AURA."""

    def __init__(self, name: str = SERVER_NAME, version: str = SERVER_VERSION):
        self.name = name
        self.version = version
        self.initialized = False
        self.client_info = {}

    def log(self, message: str):
        """Log diagnostic messages to stderr (never stdout)."""
        sys.stderr.write(f"[{self.name}] {message}\n")
        sys.stderr.flush()

    # ── Protocol Handlers ─────────────────────────────────────────────────────

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'initialize' handshake."""
        self.client_info = params.get("clientInfo", {})
        client_version = params.get("protocolVersion", MCP_PROTOCOL_VERSION)
        self.log(f"Initializing connection with client: {self.client_info.get('name', 'unknown')} (protocol: {client_version})")

        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
                "logging": {},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
            "instructions": "AURA Model Context Protocol Server for Windows desktop and browser automation.",
        }

    def handle_tools_list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle 'tools/list' request."""
        tools_mcp = [t.to_mcp_dict() for t in ALL_TOOLS]
        return {"tools": tools_mcp}

    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'tools/call' request."""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("Tool name is required in params.")

        tool = get_tool(name)
        if not tool:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Tool '{name}' not found. Available tools: {[t.name for t in ALL_TOOLS]}",
                    }
                ],
                "isError": True,
            }

        self.log(f"Executing tool '{name}' with args: {arguments}")
        try:
            result = tool.handler(**arguments)
            # Format result text
            if isinstance(result, (dict, list)):
                result_text = json.dumps(result, indent=2)
            else:
                result_text = str(result)

            is_error = False
            if isinstance(result, dict) and result.get("status") in ("failure", "error"):
                is_error = True

            return {
                "content": [{"type": "text", "text": result_text}],
                "isError": is_error,
            }
        except Exception as e:
            self.log(f"Tool execution failed: {e}\n{traceback.format_exc()}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Tool execution failed with error: {str(e)}",
                    }
                ],
                "isError": True,
            }

    def handle_resources_list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle 'resources/list' request."""
        resources = [r.to_mcp_dict() for r in get_all_resources()]
        return {"resources": resources}

    def handle_resources_templates_list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle 'resources/templates/list' request."""
        return {
            "resourceTemplates": [
                {
                    "uriTemplate": "aura://agents/{agent_name}",
                    "name": "Single Agent Information",
                    "description": "Information and schema for a specific AURA agent.",
                    "mimeType": "application/json",
                },
                {
                    "uriTemplate": "aura://app-maps/{app_name}",
                    "name": "Single App UI Map",
                    "description": "Parsed UI App Map for a specific application.",
                    "mimeType": "application/json",
                },
            ]
        }

    def handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'resources/read' request."""
        uri = params.get("uri")
        if not uri:
            raise ValueError("URI is required in params.")

        content = read_resource(uri)
        if content is None:
            raise ValueError(f"Resource not found: '{uri}'")

        return {"contents": [content]}

    def handle_prompts_list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle 'prompts/list' request."""
        prompts = [p.to_mcp_dict() for p in ALL_PROMPTS]
        return {"prompts": prompts}

    def handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'prompts/get' request."""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("Prompt name is required in params.")

        prompt = get_prompt(name)
        if not prompt:
            raise ValueError(f"Prompt '{name}' not found.")

        messages = prompt.handler(**arguments)
        return {
            "description": prompt.description,
            "messages": messages,
        }

    # ── JSON-RPC 2.0 Message Dispatcher ───────────────────────────────────────

    def process_message(self, message_str: str) -> Optional[str]:
        """
        Process an incoming JSON-RPC 2.0 request or notification string.
        Returns a JSON response string, or None if message was a notification.
        """
        if not message_str or not message_str.strip():
            return None

        try:
            req = json.loads(message_str)
        except json.JSONDecodeError as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": JSONRPCErrorCodes.PARSE_ERROR,
                    "message": f"Parse error: {str(e)}",
                },
            })

        # Batch requests
        if isinstance(req, list):
            responses = []
            for sub_req in req:
                res = self._dispatch_single(sub_req)
                if res is not None:
                    responses.append(res)
            return json.dumps(responses) if responses else None

        res = self._dispatch_single(req)
        return json.dumps(res) if res is not None else None

    def _dispatch_single(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": req.get("id") if isinstance(req, dict) else None,
                "error": {
                    "code": JSONRPCErrorCodes.INVALID_REQUEST,
                    "message": "Invalid JSON-RPC 2.0 request.",
                },
            }

        msg_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        # Handle notifications (no id)
        if msg_id is None and not ("id" in req):
            if method == "notifications/initialized":
                self.initialized = True
                self.log("Client completed initialization.")
            return None

        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = self.handle_tools_call(params)
            elif method == "resources/list":
                result = self.handle_resources_list(params)
            elif method == "resources/templates/list":
                result = self.handle_resources_templates_list(params)
            elif method == "resources/read":
                result = self.handle_resources_read(params)
            elif method == "prompts/list":
                result = self.handle_prompts_list(params)
            elif method == "prompts/get":
                result = self.handle_prompts_get(params)
            elif method == "logging/setLevel":
                result = {}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": JSONRPCErrorCodes.METHOD_NOT_FOUND,
                        "message": f"Method '{method}' not found.",
                    },
                }

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }

        except ValueError as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": JSONRPCErrorCodes.INVALID_PARAMS,
                    "message": str(e),
                },
            }
        except Exception as e:
            self.log(f"Internal error on {method}: {e}\n{traceback.format_exc()}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": JSONRPCErrorCodes.INTERNAL_ERROR,
                    "message": f"Internal server error: {str(e)}",
                },
            }

    # ── Transports ────────────────────────────────────────────────────────────

    def run_stdio(self):
        """Run the MCP server over standard I/O (stdin/stdout)."""
        self.log(f"Starting {self.name} v{self.version} stdio transport...")
        # Ensure stdout is in unbuffered or line-buffered mode
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")

        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue

            response = self.process_message(line_str)
            if response:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()

    def run_sse(self, host: str = "127.0.0.1", port: int = 8000):
        """Run the MCP server over HTTP / SSE transport."""
        from http.server import HTTPServer, BaseHTTPRequestHandler

        server_instance = self

        class MCPHTTPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health" or self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok", "server": server_instance.name}).encode("utf-8"))
                elif self.path == "/mcp/tools":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(server_instance.handle_tools_list()).encode("utf-8"))
                elif self.path == "/mcp/resources":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(server_instance.handle_resources_list()).encode("utf-8"))
                elif self.path == "/mcp/prompts":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(server_instance.handle_prompts_list()).encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")

                response = server_instance.process_message(body)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                if response:
                    self.wfile.write(response.encode("utf-8"))
                else:
                    self.wfile.write(b"{}")

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

            def log_message(self, format, *args):
                server_instance.log(f"HTTP: {format % args}")

        server_instance.log(f"Starting {self.name} HTTP server on http://{host}:{port} ...")
        httpd = HTTPServer((host, port), MCPHTTPHandler)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            server_instance.log("Server stopped.")
