"""
Tests for AURA MCP Tool Handlers.
"""

from automation.mcp.tools import (
    handle_execute_prompt,
    handle_list_agents,
    handle_get_agent_info,
    handle_get_app_map,
    handle_verify_state,
    handle_send_input,
)


def test_handle_list_agents():
    result = handle_list_agents()
    assert "agents" in result
    assert "notepad" in result["agents"]
    assert result["agents"]["notepad"]["app_name"] == "Notepad"


def test_handle_get_agent_info():
    result = handle_get_agent_info("notepad")
    assert result["status"] == "success"
    assert result["agent_name"] == "notepad"
    assert "type" in result["capabilities"]["actions"]


def test_handle_get_app_map():
    result = handle_get_app_map("notepad")
    assert result["status"] == "success"
    assert result["application"] == "notepad"
    assert "text_editor" in result["elements"]


def test_handle_execute_prompt_dry_run():
    result = handle_execute_prompt("Open Notepad, type AURA Rocks, and save as aura.txt", dry_run=True)
    assert result["status"] == "dry_run"
    assert len(result["planned_actions"]) >= 2
    actions = [a["action"] for a in result["planned_actions"]]
    assert "open" in actions
    assert "type" in actions


def test_handle_verify_state_window_closed():
    result = handle_verify_state("window_closed", "NonExistentWindow_XYZ_12345")
    assert result["verified"] is True
