#!/usr/bin/env python
"""
AURA MCP Server — Root Entrypoint.

Usage:
    python mcp_server.py                     # Start MCP stdio server (default)
    python mcp_server.py --transport http   # Start MCP HTTP server on port 8000
    python mcp_server.py --list-tools       # View available tools
    python mcp_server.py --generate-configs # Generate Claude/Cursor/Cline configs
"""

import sys
import os

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from automation.mcp.cli import main

if __name__ == "__main__":
    main()
