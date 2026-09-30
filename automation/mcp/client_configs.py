"""
AURA MCP Client Configs Generator — Auto-generates configuration files for Claude Desktop, Cursor, Antigravity, Cline, and Windsurf.
"""

from __future__ import annotations
import json
import os
import sys
from typing import Any, Dict


def get_server_command(root_dir: str | None = None) -> tuple[str, list[str]]:
    """Determine the python executable and arguments for launching AURA MCP."""
    python_exe = sys.executable
    if root_dir is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    args = ["-m", "automation.mcp"]
    return python_exe, args


def generate_claude_desktop_config(root_dir: str | None = None) -> Dict[str, Any]:
    """Generate configuration for Claude Desktop."""
    python_exe, args = get_server_command(root_dir)
    if root_dir is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return {
        "mcpServers": {
            "aura": {
                "command": python_exe,
                "args": args,
                "cwd": root_dir,
                "env": {
                    "PYTHONPATH": root_dir,
                    "PYTHONUNBUFFERED": "1",
                },
            }
        }
    }


def generate_cursor_config(root_dir: str | None = None) -> Dict[str, Any]:
    """Generate configuration for Cursor IDE."""
    python_exe, args = get_server_command(root_dir)
    if root_dir is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return {
        "mcpServers": {
            "aura": {
                "command": python_exe,
                "args": args,
                "cwd": root_dir,
                "env": {
                    "PYTHONPATH": root_dir,
                },
            }
        }
    }


def generate_cline_config(root_dir: str | None = None) -> Dict[str, Any]:
    """Generate configuration for VS Code Cline / Roo Code."""
    python_exe, args = get_server_command(root_dir)
    if root_dir is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return {
        "mcpServers": {
            "aura": {
                "command": python_exe,
                "args": args,
                "cwd": root_dir,
                "env": {
                    "PYTHONPATH": root_dir,
                },
                "disabled": False,
                "autoApprove": [
                    "aura_list_agents",
                    "aura_get_agent_info",
                    "aura_list_windows",
                    "aura_inspect_window",
                    "aura_find_element",
                    "aura_get_app_map",
                ],
            }
        }
    }


def generate_antigravity_config(root_dir: str | None = None) -> Dict[str, Any]:
    """Generate configuration for Google Antigravity / Gemini."""
    python_exe, args = get_server_command(root_dir)
    if root_dir is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return {
        "mcp": {
            "servers": {
                "aura": {
                    "command": python_exe,
                    "args": args,
                    "cwd": root_dir,
                    "env": {
                        "PYTHONPATH": root_dir,
                    },
                }
            }
        }
    }


def write_all_configs(output_dir: str | None = None):
    """Write sample configuration files into the project root."""
    if output_dir is None:
        output_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    claude_cfg = generate_claude_desktop_config(output_dir)
    cursor_cfg = generate_cursor_config(output_dir)
    cline_cfg = generate_cline_config(output_dir)
    agy_cfg = generate_antigravity_config(output_dir)

    with open(os.path.join(output_dir, "claude_desktop_config.example.json"), "w", encoding="utf-8") as f:
        json.dump(claude_cfg, f, indent=2)

    with open(os.path.join(output_dir, "cursor_mcp.example.json"), "w", encoding="utf-8") as f:
        json.dump(cursor_cfg, f, indent=2)

    with open(os.path.join(output_dir, "cline_mcp.example.json"), "w", encoding="utf-8") as f:
        json.dump(cline_cfg, f, indent=2)

    with open(os.path.join(output_dir, "antigravity_mcp.example.json"), "w", encoding="utf-8") as f:
        json.dump(agy_cfg, f, indent=2)
