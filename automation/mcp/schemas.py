"""
AURA MCP Schemas — Protocol types, tool definitions, resource descriptors, and prompt templates.
Compliant with Model Context Protocol specification 2024-11-05.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union


# ── MCP Protocol Version ──────────────────────────────────────────────────────
MCP_PROTOCOL_VERSION = "2024-11-05"
SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2024-10-07"]
SERVER_NAME = "aura-mcp"
SERVER_VERSION = "1.0.0"


# ── Tool Definition ──────────────────────────────────────────────────────────
@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]

    def to_mcp_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


# ── Resource Definition ───────────────────────────────────────────────────────
@dataclass
class ResourceDefinition:
    uri: str
    name: str
    description: str
    mime_type: str
    handler: Callable[[str], Union[str, bytes, Dict[str, Any]]]

    def to_mcp_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


# ── Prompt Definition ────────────────────────────────────────────────────────
@dataclass
class PromptArgument:
    name: str
    description: str
    required: bool = True

    def to_mcp_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }


@dataclass
class PromptDefinition:
    name: str
    description: str
    arguments: List[PromptArgument]
    handler: Callable[..., List[Dict[str, Any]]]

    def to_mcp_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [arg.to_mcp_dict() for arg in self.arguments],
        }


# ── JSON-RPC 2.0 Error Codes ──────────────────────────────────────────────────
class JSONRPCErrorCodes:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32000
    SERVER_ERROR_END = -32099
