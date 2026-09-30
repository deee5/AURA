# AURA — Agentic UI Routing Assistant

<p align="center">
  <b>Production-Grade Windows Desktop & Browser Automation with Model Context Protocol (MCP) Integration</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/MCP-2024--11--05-blue.svg" alt="MCP Version" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg" alt="Python Version" />
  <img src="https://img.shields.io/badge/Tests-18%20Passed-success.svg" alt="Tests" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

---

## 📖 Overview

**AURA (Agentic UI Routing Assistant)** is an agentic automation framework engineered for Windows desktop and web applications. It bridges Large Language Models (LLMs) to desktop control through deterministic UI maps, accessibility tree inspection (UI Automation / `pywinauto`), safe input simulation, and now a **complete Model Context Protocol (MCP) Server**.

With AURA's MCP server, any modern AI environment—including **Claude Desktop**, **Cursor IDE**, **Google Antigravity**, **VS Code (Cline / Roo Code)**, and **Windsurf**—can natively inspect, orchestrate, and control Windows applications and web workflows.

---

## 🚀 Key Features

- 🔌 **Standard Model Context Protocol (MCP) Support**: Full compliance with the MCP specification (2024-11-05), featuring **14 tools**, **6 dynamic resources**, and **4 workflow prompts**.
- 🖥️ **Desktop & Web Agents**:
  - **Notepad Agent**: Launch, safe caret-preserving clipboard typing, save/save as, copy/paste, and close with safety gates.
  - **Browser Agent**: Playwright-powered portal automation with session persistence.
- 🛡️ **Anti-Key-Bounce Safe Typing**: Prevents Windows 11 UWP key repeat stuttering (e.g. typing `"TTSALA"` instead of `"TSALA"`) via high-precision clipboard injection.
- 🎯 **3-Tier Element Resolver**:
  - *Tier 1*: Deterministic UI App Map lookup (`app_maps/*.json`).
  - *Tier 2*: Live UIA accessibility tree heuristic matching.
  - *Tier 3*: Fallback inspection and diagnostics.
- 🔍 **Live UI Inspection & Window Management**: Enumerate top-level windows, inspect accessibility trees, and find elements by name, automation ID, or control type.
- 🔄 **Dual Transport**: Supports standard **stdio** (JSON-RPC 2.0) and **HTTP / SSE** servers.
- 🧩 **Extensible Plugin Architecture**: Create new application agents in minutes following the 3-step plugin blueprint.

---

## 🛠️ MCP Tools Reference (14 Tools)

| Tool | Purpose |
|:---|:---|
| `aura_execute_prompt` | End-to-end natural language automation with agent planning and execution (supports `dry_run`). |
| `aura_list_agents` | Lists all discovered agents, their capabilities, and running states. |
| `aura_get_agent_info` | Retrieves detailed metadata and action schemas for a specific agent. |
| `aura_execute_agent_action` | Directly executes an action on an agent (`notepad.open`, `notepad.type`, etc.). |
| `aura_list_windows` | Lists all open top-level application windows on the desktop. |
| `aura_focus_window` | Brings a window matching title/class to the foreground and focuses it. |
| `aura_launch_app` | Launches an executable and waits for its window to appear. |
| `aura_close_window` | Closes an application window gracefully. |
| `aura_inspect_window` | Traverses the live UIA accessibility tree of a window down to a specified depth. |
| `aura_find_element` | Finds a UI element inside an active window matching multi-property criteria. |
| `aura_send_input` | Sends safe keyboard input (`text`, `hotkey`, or `key_sequence`). |
| `aura_verify_state` | Verifies post-action state (`window_exists`, `window_closed`, `text_contains`, `element_exists`). |
| `aura_get_app_map` | Retrieves the parsed UI App Map JSON for an application. |
| `aura_take_screenshot` | Captures a screenshot of a specific window or the full desktop. |

---

## 📡 Dynamic MCP Resources (`aura://...`)

| Resource URI | Description |
|:---|:---|
| `aura://system/status` | System health, version, registered agent count, platform info. |
| `aura://agents` | Overview of all active agents and their capabilities. |
| `aura://agents/{agent_name}` | Detailed metadata and action schemas for a specific agent. |
| `aura://windows/open` | Live list of visible open desktop application windows. |
| `aura://app-maps` | Index of available UI App Map definitions. |
| `aura://app-maps/{app_name}` | Full UI element tree and selectors for an application. |

---

## 💡 Workflow Prompts

- `aura_orchestrate_task`: Guides an LLM to plan, verify, and execute multi-step desktop workflows.
- `aura_build_new_agent`: Scaffolds a new agent and app map following AURA's plugin architecture.
- `aura_debug_ui_tree`: Diagnoses UI tree locators and automation IDs.
- `aura_safety_review`: Audits actions for destructive risks before running.

---

## 📦 Installation & Quickstart

### 1. Install Requirements

```bash
git clone https://github.com/ambrishchaurasia/AURA.git
cd AURA

pip install -r requirements.txt
# Or in editable mode:
pip install -e .
```

### 2. Run the MCP Server

```bash
# Standard stdio mode (for Claude Desktop, Cursor, Cline, etc.):
python mcp_server.py

# Or via console script:
aura-mcp

# Or start in HTTP / SSE mode on port 8000:
python mcp_server.py --transport http --port 8000
```

### 3. Generate Client Configuration Files

```bash
python mcp_server.py --generate-configs
```

This creates ready-to-copy configurations:
- `claude_desktop_config.example.json`
- `cursor_mcp.example.json`
- `cline_mcp.example.json`
- `antigravity_mcp.example.json`

---

## 🔌 Connecting to MCP Clients

### Claude Desktop
Add to `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "aura": {
      "command": "python",
      "args": ["-m", "automation.mcp"],
      "cwd": "C:\\path\\to\\AURA",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\AURA",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Cursor IDE
Add to `.cursor/mcp.json` or Cursor MCP settings:
```json
{
  "mcpServers": {
    "aura": {
      "command": "python",
      "args": ["-m", "automation.mcp"],
      "cwd": "C:\\path\\to\\AURA",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\AURA"
      }
    }
  }
}
```

### Google Antigravity / Gemini
Add to `.gemini/antigravity.json`:
```json
{
  "mcp": {
    "servers": {
      "aura": {
        "command": "python",
        "args": ["-m", "automation.mcp"],
        "cwd": "C:\\path\\to\\AURA",
        "env": {
          "PYTHONPATH": "C:\\path\\to\\AURA"
        }
      }
    }
  }
}
```

---

## 🌐 Running the Full Stack (React UI + Backend API)

To run the full stack web application:

1. **Start Backend API & MCP Server**:
   ```bash
   python -m automation.api
   # Starts Flask API + MCP endpoints on http://127.0.0.1:5000
   ```

2. **Start React Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   # Opens http://localhost:5173
   ```

---

## 🧪 Testing

Run the automated test suite:

```bash
pytest
```

---

## 📁 Repository Structure

```
AURA/
├── automation/
│   ├── mcp/                      # Model Context Protocol Server Package
│   │   ├── __init__.py           # Package exports
│   │   ├── server.py             # JSON-RPC 2.0 protocol engine (stdio & HTTP/SSE)
│   │   ├── tools.py              # 14 MCP Tool implementations
│   │   ├── resources.py          # Dynamic aura:// resources
│   │   ├── prompts.py            # Workflow prompt templates
│   │   ├── schemas.py            # Types and protocol schemas
│   │   ├── cli.py                # Command-line interface
│   │   └── client_configs.py     # Configuration generator
│   ├── agents/                   # Pluggable Application Agents
│   │   ├── notepad_agent.py      # Windows Notepad agent
│   │   └── browser_agent.py      # MyUPES Portal agent (Playwright)
│   ├── core/                     # AURA Core Engine
│   │   ├── base_agent.py         # Abstract agent base contract
│   │   ├── registry.py           # Auto-discovery agent registry
│   │   ├── window_manager.py     # Window finding, focusing, launching
│   │   ├── element_finder.py     # Multi-property UIA element search
│   │   ├── input_handler.py      # Safe clipboard typing & hotkeys
│   │   ├── app_map.py            # JSON App Map parser
│   │   ├── resolver.py           # Tiered UI resolver
│   │   ├── verifier.py           # Post-action state verification
│   │   ├── planner.py            # Offline rule-based planner
│   │   ├── llm_orchestrator.py   # Gemini LLM orchestrator
│   │   └── logger.py             # Structured JSON task logging
│   └── api.py                    # Flask REST API + MCP Endpoints
├── app_maps/                     # UI App Maps for applications
│   ├── notepad.json
│   ├── browser.json
│   └── developer_guide.md
├── frontend/                     # React + Vite Web UI
├── tests/                        # Automated Tests
│   ├── test_mcp_protocol.py      # JSON-RPC 2.0 protocol tests
│   └── test_mcp_tools.py         # MCP tool unit tests
├── mcp_server.py                 # Standalone MCP server entrypoint
├── MCP_GUIDE.md                  # Comprehensive MCP developer guide
├── pyproject.toml                # Package configuration & console script
├── requirements.txt              # Project dependencies
└── README.md                     # Project documentation
```

---

## 📄 License

MIT License. See `LICENSE` for details.
