"""
Tests for AURA MCP Server JSON-RPC 2.0 Protocol Compliance.
"""

import json
import pytest
from automation.mcp.server import MCPServer
from automation.mcp.schemas import JSONRPCErrorCodes, MCP_PROTOCOL_VERSION


@pytest.fixture
def server():
    return MCPServer()


def test_initialize_handshake(server):
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "clientInfo": {"name": "pytest-client", "version": "1.0.0"},
        },
    }
    resp_str = server.process_message(json.dumps(req))
    assert resp_str is not None
    resp = json.loads(resp_str)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "result" in resp
    assert resp["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert "tools" in resp["result"]["capabilities"]
    assert "resources" in resp["result"]["capabilities"]
    assert "prompts" in resp["result"]["capabilities"]
    assert resp["result"]["serverInfo"]["name"] == "aura-mcp"


def test_ping(server):
    req = {"jsonrpc": "2.0", "id": "test-ping-1", "method": "ping", "params": {}}
    resp = json.loads(server.process_message(json.dumps(req)))
    assert resp["id"] == "test-ping-1"
    assert resp["result"] == {}


def test_tools_list(server):
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    resp = json.loads(server.process_message(json.dumps(req)))
    assert "tools" in resp["result"]
    tool_names = [t["name"] for t in resp["result"]["tools"]]
    assert "aura_execute_prompt" in tool_names
    assert "aura_list_agents" in tool_names
    assert "aura_get_agent_info" in tool_names
    assert "aura_execute_agent_action" in tool_names
    assert "aura_list_windows" in tool_names
    assert "aura_inspect_window" in tool_names
    assert "aura_send_input" in tool_names
    assert "aura_verify_state" in tool_names
    assert "aura_get_app_map" in tool_names
    assert "aura_take_screenshot" in tool_names


def test_tools_call_list_agents(server):
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "aura_list_agents",
            "arguments": {},
        },
    }
    resp = json.loads(server.process_message(json.dumps(req)))
    assert resp["id"] == 3
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert "agents" in content
    assert "notepad" in content["agents"]


def test_tools_call_execute_prompt_dry_run(server):
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "aura_execute_prompt",
            "arguments": {
                "prompt": "Open Notepad and type Hello World",
                "dry_run": True,
            },
        },
    }
    resp = json.loads(server.process_message(json.dumps(req)))
    assert resp["id"] == 4
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["status"] == "dry_run"
    assert len(content["planned_actions"]) >= 1


def test_tools_call_unknown_tool(server):
    req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "non_existent_tool",
            "arguments": {},
        },
    }
    resp = json.loads(server.process_message(json.dumps(req)))
    assert resp["result"]["isError"] is True
    assert "not found" in resp["result"]["content"][0]["text"]


def test_resources_list(server):
    req = {"jsonrpc": "2.0", "id": 6, "method": "resources/list", "params": {}}
    resp = json.loads(server.process_message(json.dumps(req)))
    uris = [r["uri"] for r in resp["result"]["resources"]]
    assert "aura://system/status" in uris
    assert "aura://agents" in uris
    assert "aura://windows/open" in uris
    assert "aura://app-maps" in uris


def test_resources_read_system_status(server):
    req = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "resources/read",
        "params": {"uri": "aura://system/status"},
    }
    resp = json.loads(server.process_message(json.dumps(req)))
    contents = resp["result"]["contents"]
    assert len(contents) == 1
    data = json.loads(contents[0]["text"])
    assert data["server"] == "aura-mcp"
    assert data["status"] == "online"


def test_resources_read_app_map(server):
    req = {
        "jsonrpc": "2.0",
        "id": 8,
        "method": "resources/read",
        "params": {"uri": "aura://app-maps/notepad"},
    }
    resp = json.loads(server.process_message(json.dumps(req)))
    contents = resp["result"]["contents"]
    data = json.loads(contents[0]["text"])
    assert data["application"] == "notepad"
    assert "text_editor" in data["elements"]


def test_prompts_list(server):
    req = {"jsonrpc": "2.0", "id": 9, "method": "prompts/list", "params": {}}
    resp = json.loads(server.process_message(json.dumps(req)))
    prompt_names = [p["name"] for p in resp["result"]["prompts"]]
    assert "aura_orchestrate_task" in prompt_names
    assert "aura_build_new_agent" in prompt_names
    assert "aura_debug_ui_tree" in prompt_names
    assert "aura_safety_review" in prompt_names


def test_prompts_get(server):
    req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "prompts/get",
        "params": {
            "name": "aura_orchestrate_task",
            "arguments": {"goal": "Write report in Notepad"},
        },
    }
    resp = json.loads(server.process_message(json.dumps(req)))
    assert "messages" in resp["result"]
    assert len(resp["result"]["messages"]) >= 1
    assert "Write report in Notepad" in resp["result"]["messages"][0]["content"]["text"]


def test_method_not_found(server):
    req = {"jsonrpc": "2.0", "id": 99, "method": "unknown_method", "params": {}}
    resp = json.loads(server.process_message(json.dumps(req)))
    assert resp["error"]["code"] == JSONRPCErrorCodes.METHOD_NOT_FOUND


def test_invalid_json(server):
    resp = json.loads(server.process_message("not valid json{"))
    assert resp["error"]["code"] == JSONRPCErrorCodes.PARSE_ERROR
