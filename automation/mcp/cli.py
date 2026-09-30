"""
AURA MCP Command-Line Interface.
Run stdio or HTTP MCP server, inspect tools/resources/prompts, or generate client configs.
"""

from __future__ import annotations
import argparse
import json
import os
import sys

from automation.mcp.server import MCPServer
from automation.mcp.tools import ALL_TOOLS
from automation.mcp.resources import get_all_resources
from automation.mcp.prompts import ALL_PROMPTS
from automation.mcp.client_configs import write_all_configs


def main():
    parser = argparse.ArgumentParser(
        description="AURA Model Context Protocol (MCP) Server for Windows & Browser Automation"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport protocol: 'stdio' (default, for Claude/Cursor/Cline) or 'sse'/'http'",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind for HTTP/SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for HTTP/SSE transport (default: 8000)",
    )
    parser.add_argument(
        "--generate-configs",
        action="store_true",
        help="Generate example MCP configuration files for Claude Desktop, Cursor, Antigravity, and Cline",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all MCP tools with descriptions and parameters",
    )
    parser.add_argument(
        "--list-resources",
        action="store_true",
        help="List all dynamic and static MCP resources",
    )
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="List all MCP workflow prompts",
    )
    parser.add_argument(
        "--test-ping",
        action="store_true",
        help="Run an in-memory JSON-RPC ping test",
    )

    args = parser.parse_args()

    if args.generate_configs:
        write_all_configs()
        print("Generated example configuration files:")
        print("  - claude_desktop_config.example.json")
        print("  - cursor_mcp.example.json")
        print("  - cline_mcp.example.json")
        print("  - antigravity_mcp.example.json")
        return

    if args.list_tools:
        print(f"\nAURA MCP Tools ({len(ALL_TOOLS)} available):")
        print("=" * 60)
        for t in ALL_TOOLS:
            print(f"• {t.name}:")
            print(f"  {t.description}")
            props = t.input_schema.get("properties", {})
            if props:
                print("  Parameters:")
                for p_name, p_info in props.items():
                    req = " (required)" if p_name in t.input_schema.get("required", []) else ""
                    print(f"    - {p_name} [{p_info.get('type', 'any')}]{req}: {p_info.get('description', '')}")
            print()
        return

    if args.list_resources:
        resources = get_all_resources()
        print(f"\nAURA MCP Resources ({len(resources)} available):")
        print("=" * 60)
        for r in resources:
            print(f"• {r.uri} ({r.mime_type})")
            print(f"  {r.name}: {r.description}\n")
        return

    if args.list_prompts:
        print(f"\nAURA MCP Prompts ({len(ALL_PROMPTS)} available):")
        print("=" * 60)
        for p in ALL_PROMPTS:
            print(f"• {p.name}:")
            print(f"  {p.description}")
            if p.arguments:
                print("  Arguments:")
                for a in p.arguments:
                    req = " (required)" if a.required else " (optional)"
                    print(f"    - {a.name}{req}: {a.description}")
            print()
        return

    if args.test_ping:
        server = MCPServer()
        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "test-client"}},
        })
        resp = server.process_message(init_req)
        print("Initialize response:", resp)

        tools_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })
        resp2 = server.process_message(tools_req)
        tools_data = json.loads(resp2)
        print(f"Tools list success! {len(tools_data['result']['tools'])} tools loaded.")
        return

    # Start Server
    server = MCPServer()
    if args.transport == "stdio":
        server.run_stdio()
    else:
        server.run_sse(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
