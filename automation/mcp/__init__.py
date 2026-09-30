"""
AURA Model Context Protocol (MCP) Integration.
Enables full desktop & browser control via Claude Desktop, Cursor, Antigravity, VS Code, and any MCP-compliant client.
"""

from __future__ import annotations

from automation.mcp.schemas import (
    MCP_PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    ToolDefinition,
    ResourceDefinition,
    PromptDefinition,
)
from automation.mcp.server import MCPServer
from automation.mcp.tools import ALL_TOOLS, get_tool
from automation.mcp.resources import get_all_resources, read_resource
from automation.mcp.prompts import ALL_PROMPTS, get_prompt
from automation.mcp.cli import main

__all__ = [
    "MCPServer",
    "ALL_TOOLS",
    "ALL_PROMPTS",
    "get_tool",
    "get_prompt",
    "get_all_resources",
    "read_resource",
    "main",
    "MCP_PROTOCOL_VERSION",
    "SERVER_NAME",
    "SERVER_VERSION",
]
