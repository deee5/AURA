"""
AURA MCP Tools — Complete tool suite for Windows desktop & browser automation via MCP.
Provides 14 robust tools covering prompt execution, direct agent actions, window management,
UI inspection, keyboard/mouse input, state verification, app maps, and screenshots.
"""

from __future__ import annotations
import base64
import io
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

from automation.mcp.schemas import ToolDefinition
from automation.core.registry import registry
from automation.core import window_manager
from automation.core import element_finder
from automation.core import input_handler
from automation.core import verifier as verify_module
from automation.core.app_map import load_app_map
from automation.core.planner import SimplePlanner
from automation.core.logger import TaskLog


# ── Tool 1: Execute Natural Language Prompt ───────────────────────────────────
def handle_execute_prompt(prompt: str, dry_run: bool = False) -> Dict[str, Any]:
    """Execute a natural language automation prompt across AURA agents."""
    if not prompt or not prompt.strip():
        return {"status": "error", "message": "Prompt cannot be empty", "steps": []}

    prompt = prompt.strip()
    plan_result = None
    planner_source = "offline_rule_planner"

    # Try LLM Orchestrator first if GEMINI_API_KEY is present
    if os.environ.get("GEMINI_API_KEY"):
        try:
            from automation.core.llm_orchestrator import LLMOrchestrator
            orchestrator = LLMOrchestrator()
            plan_result = orchestrator.plan(prompt)
            planner_source = "llm_orchestrator"
        except Exception as e:
            print(f"[AURA-MCP] LLM Orchestrator failed, falling back to rule planner: {e}", file=sys.stderr)

    # Fallback to SimplePlanner
    if not plan_result or (not plan_result.get("actions") and not plan_result.get("message")):
        rule_planner = SimplePlanner()
        actions = rule_planner.plan(prompt)
        plan_result = {
            "message": f"Planned {len(actions)} step(s) via offline rule planner.",
            "actions": actions,
        }
        planner_source = "rule_planner"

    actions = plan_result.get("actions", [])
    message = plan_result.get("message", "")

    if dry_run:
        return {
            "status": "dry_run",
            "prompt": prompt,
            "planner": planner_source,
            "message": message,
            "planned_actions": actions,
            "total_steps": len(actions),
        }

    if not actions and not message:
        return {
            "status": "error",
            "prompt": prompt,
            "message": "Could not understand any actionable steps from the prompt.",
            "steps": [],
        }

    # Execute planned actions
    task_id = str(uuid.uuid4())[:8]
    log = TaskLog(task_id, prompt)
    steps_results = []
    task_status = "COMPLETED"

    for idx, act in enumerate(actions, 1):
        agent_name = act.get("agent", "unknown")
        action_name = act.get("action")
        params = act.get("params", {})

        log.start_step(action_name, application=agent_name)
        agent = registry.get_agent(agent_name)

        if agent:
            result = agent.execute(action_name, params)
        else:
            result = {
                "status": "failure",
                "action": action_name,
                "details": f"Unknown agent: '{agent_name}'. Available agents: {list(registry.get_all_agents().keys())}",
                "duration_ms": 0,
            }

        step_status = result.get("status", "failure")
        details = result.get("details", "")
        duration_ms = result.get("duration_ms", 0)

        if step_status == "success":
            log.complete_step(status="success", details=details)
        else:
            log.fail_step(error=details, details=details)
            task_status = "FAILED"

        steps_results.append({
            "step": idx,
            "agent": agent_name,
            "action": action_name,
            "params": params,
            "status": step_status,
            "details": details,
            "duration_ms": duration_ms,
        })

        if step_status == "failure":
            break

    log.finish("completed" if task_status == "COMPLETED" else "failed")

    return {
        "task_id": task_id,
        "status": task_status,
        "planner": planner_source,
        "prompt": prompt,
        "message": message,
        "steps": steps_results,
        "total_executed": len(steps_results),
    }


# ── Tool 2: List Registered Agents ───────────────────────────────────────────
def handle_list_agents() -> Dict[str, Any]:
    """List all registered AURA automation agents and their capabilities."""
    all_agents = registry.get_all_agents()
    agents_summary = {}

    for name, agent in all_agents.items():
        try:
            caps = agent.get_capabilities()
        except Exception:
            caps = {}

        try:
            is_running = agent.is_running()
        except Exception:
            is_running = False

        agents_summary[name] = {
            "name": name,
            "app_name": getattr(agent, "app_name", name),
            "process_name": getattr(agent, "process_name", "unknown"),
            "is_running": is_running,
            "capabilities": caps.get("actions", {}),
            "description": agent.get_llm_capabilities().strip(),
        }

    return {
        "count": len(agents_summary),
        "agents": agents_summary,
    }


# ── Tool 3: Get Single Agent Info ────────────────────────────────────────────
def handle_get_agent_info(agent_name: str) -> Dict[str, Any]:
    """Get deep information, schema, and capabilities for a specific agent."""
    agent = registry.get_agent(agent_name)
    if not agent:
        return {
            "status": "error",
            "message": f"Agent '{agent_name}' not found.",
            "available_agents": list(registry.get_all_agents().keys()),
        }

    app_map = load_app_map(agent_name)
    app_map_elements = list(app_map.elements.keys()) if app_map else []

    return {
        "status": "success",
        "agent_name": agent_name,
        "app_name": getattr(agent, "app_name", agent_name),
        "process_name": getattr(agent, "process_name", "unknown"),
        "is_running": agent.is_running(),
        "capabilities": agent.get_capabilities(),
        "llm_capabilities_prompt": agent.get_llm_capabilities(),
        "has_app_map": app_map is not None,
        "app_map_elements": app_map_elements,
    }


# ── Tool 4: Execute Action on Agent ──────────────────────────────────────────
def handle_execute_agent_action(
    agent_name: str, action: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Directly execute an action on a specific agent."""
    agent = registry.get_agent(agent_name)
    if not agent:
        return {
            "status": "failure",
            "action": action,
            "details": f"Agent '{agent_name}' not found in registry.",
            "available_agents": list(registry.get_all_agents().keys()),
            "duration_ms": 0,
        }

    params = params or {}
    start_time = time.time()
    try:
        result = agent.execute(action, params)
        if not isinstance(result, dict):
            result = {"status": "success", "details": str(result)}
        if "duration_ms" not in result:
            result["duration_ms"] = round((time.time() - start_time) * 1000)
        return result
    except Exception as e:
        return {
            "status": "failure",
            "action": action,
            "details": f"Execution error: {str(e)}",
            "duration_ms": round((time.time() - start_time) * 1000),
        }


# ── Tool 5: List Windows ─────────────────────────────────────────────────────
def handle_list_windows(
    title_filter: Optional[str] = None, visible_only: bool = True
) -> Dict[str, Any]:
    """List open desktop application windows."""
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        windows = []
        for win in desktop.windows():
            try:
                info = win.element_info
                name = (info.name or "").strip()
                if not name and visible_only:
                    continue
                if visible_only and not info.visible:
                    continue
                if title_filter and title_filter.lower() not in name.lower():
                    continue

                rect = info.rectangle
                windows.append({
                    "title": name,
                    "class_name": info.class_name or "",
                    "control_type": info.control_type or "",
                    "process_id": info.process_id,
                    "handle": info.handle,
                    "visible": info.visible,
                    "enabled": info.enabled,
                    "rectangle": {
                        "left": rect.left if rect else 0,
                        "top": rect.top if rect else 0,
                        "right": rect.right if rect else 0,
                        "bottom": rect.bottom if rect else 0,
                    } if rect else None,
                })
            except Exception:
                continue

        return {"count": len(windows), "windows": windows}
    except Exception as e:
        return {"error": f"Failed to list windows: {str(e)}", "windows": []}


# ── Tool 6: Focus Window ─────────────────────────────────────────────────────
def handle_focus_window(
    title_contains: Optional[str] = None, class_name: Optional[str] = None
) -> Dict[str, Any]:
    """Bring a window to foreground and give it keyboard focus."""
    win = window_manager.find_window(title_contains=title_contains, class_name=class_name)
    if win is None:
        return {
            "status": "failure",
            "details": f"Window not found matching title='{title_contains}', class='{class_name}'",
        }

    success = window_manager.focus_window(win)
    info = window_manager.get_window_info(win)
    return {
        "status": "success" if success else "failure",
        "details": f"Focused window '{info.get('title')}'",
        "window_info": info,
    }


# ── Tool 7: Launch Application ───────────────────────────────────────────────
def handle_launch_app(
    executable: str,
    args: Optional[List[str]] = None,
    wait_title: Optional[str] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Launch an executable or application and wait for window to appear."""
    win = window_manager.launch_application(
        executable=executable, args=args, wait_title=wait_title, timeout=timeout
    )
    if win is None:
        return {
            "status": "failure",
            "details": f"Application '{executable}' launched but window did not appear within {timeout}s",
        }

    info = window_manager.get_window_info(win)
    return {
        "status": "success",
        "details": f"Application '{executable}' launched successfully.",
        "window": info,
    }


# ── Tool 8: Close Window ─────────────────────────────────────────────────────
def handle_close_window(
    title_contains: Optional[str] = None, class_name: Optional[str] = None
) -> Dict[str, Any]:
    """Close an application window."""
    win = window_manager.find_window(title_contains=title_contains, class_name=class_name)
    if win is None:
        return {"status": "success", "details": "Window is already closed or was not found."}

    info = window_manager.get_window_info(win)
    success = window_manager.close_window(win)
    return {
        "status": "success" if success else "failure",
        "details": f"Closed window '{info.get('title')}'",
    }


# ── Tool 9: Inspect Window UI Tree ───────────────────────────────────────────
def handle_inspect_window(
    title_contains: str, max_depth: int = 4
) -> Dict[str, Any]:
    """Inspect the live UIA accessibility tree of a window."""
    win = window_manager.find_window_simple(title_contains)
    if win is None:
        return {"error": f"Window containing '{title_contains}' is not open."}

    def _build_tree(element, depth):
        if depth > max_depth:
            return None
        try:
            info = element.element_info
            node = {
                "name": info.name or "",
                "control_type": info.control_type or "",
                "automation_id": info.automation_id or "",
                "class_name": info.class_name or "",
                "enabled": info.enabled,
                "visible": info.visible,
            }
            if depth < max_depth:
                children = []
                try:
                    for child in element.children():
                        child_node = _build_tree(child, depth + 1)
                        if child_node:
                            children.append(child_node)
                except Exception:
                    pass
                if children:
                    node["children"] = children
            return node
        except Exception as e:
            return {"error": str(e)}

    tree = _build_tree(win, 0)
    return {
        "window_title": win.window_text() if hasattr(win, "window_text") else title_contains,
        "max_depth": max_depth,
        "tree": tree,
    }


# ── Tool 10: Find UI Element ─────────────────────────────────────────────────
def handle_find_element(
    window_title: str,
    name: Optional[str] = None,
    control_type: Optional[str] = None,
    automation_id: Optional[str] = None,
    class_name: Optional[str] = None,
    min_score: float = 0.5,
) -> Dict[str, Any]:
    """Search for a specific UI element inside an open window."""
    win = window_manager.find_window_simple(window_title)
    if win is None:
        return {"status": "failure", "details": f"Window '{window_title}' not found."}

    el = element_finder.find_element(
        win,
        name=name,
        control_type=control_type,
        automation_id=automation_id,
        class_name=class_name,
        min_score=min_score,
    )

    if el is None:
        return {
            "status": "not_found",
            "details": f"No element found matching criteria in '{window_title}'.",
        }

    info = element_finder._get_element_info(el)
    return {
        "status": "found",
        "element": info,
    }


# ── Tool 11: Send Input ──────────────────────────────────────────────────────
def handle_send_input(
    input_type: str,
    value: str,
    window_title: Optional[str] = None,
) -> Dict[str, Any]:
    """Send keyboard hotkey, text, or key sequence to the active window or element."""
    if window_title:
        win = window_manager.find_window_simple(window_title)
        if win:
            window_manager.focus_window(win)
            time.sleep(0.1)

    input_type = input_type.lower()
    start_time = time.time()

    if input_type == "hotkey":
        success = input_handler.send_keys(value)
        return {
            "status": "success" if success else "failure",
            "input_type": "hotkey",
            "value": value,
            "duration_ms": round((time.time() - start_time) * 1000),
        }

    elif input_type == "text":
        # Uses clipboard typing for safe entry
        success = input_handler._type_via_clipboard(value)
        return {
            "status": "success" if success else "failure",
            "input_type": "text",
            "characters": len(value),
            "duration_ms": round((time.time() - start_time) * 1000),
        }

    elif input_type == "key_sequence":
        import pyautogui
        try:
            pyautogui.press(value)
            return {"status": "success", "input_type": "key_sequence", "value": value}
        except Exception as e:
            return {"status": "failure", "details": str(e)}

    return {
        "status": "failure",
        "details": f"Invalid input_type '{input_type}'. Must be 'text', 'hotkey', or 'key_sequence'.",
    }


# ── Tool 12: Verify State ────────────────────────────────────────────────────
def handle_verify_state(
    verification_type: str,
    expected_value: Any,
    target_window: Optional[str] = None,
) -> Dict[str, Any]:
    """Run post-action state verification on windows, text, or elements."""
    vtype = verification_type.lower()

    if vtype == "window_exists":
        title = str(expected_value)
        res = verify_module.verify_window_exists(title)
        return res.to_dict()

    elif vtype == "window_closed":
        title = str(expected_value)
        res = verify_module.verify_window_closed(title)
        return res.to_dict()

    elif vtype == "text_contains":
        win = window_manager.find_window_simple(target_window or "Notepad")
        if not win:
            return {"verified": False, "details": f"Window '{target_window}' not found"}
        res = verify_module.verify_text_contains(win, str(expected_value))
        return res.to_dict()

    elif vtype == "element_exists":
        win = window_manager.find_window_simple(target_window or "")
        if not win:
            return {"verified": False, "details": f"Window '{target_window}' not found"}
        res = verify_module.verify_element_exists(win, name=str(expected_value))
        return res.to_dict()

    return {
        "verified": False,
        "details": f"Unknown verification type '{verification_type}'. Supported: 'window_exists', 'window_closed', 'text_contains', 'element_exists'.",
    }


# ── Tool 13: Get App Map ─────────────────────────────────────────────────────
def handle_get_app_map(app_name: str) -> Dict[str, Any]:
    """Get the structured JSON UI map for an application."""
    app_map = load_app_map(app_name)
    if not app_map:
        return {
            "status": "error",
            "message": f"App map for '{app_name}' not found in app_maps/ directory.",
        }

    return {
        "status": "success",
        "application": app_map.application,
        "version": app_map.version,
        "elements": app_map.elements,
    }


# ── Tool 14: Take Screenshot ─────────────────────────────────────────────────
def handle_take_screenshot(
    window_title: Optional[str] = None,
    save_path: Optional[str] = None,
    return_base64: bool = True,
) -> Dict[str, Any]:
    """Capture a screenshot of a specific window or full desktop."""
    try:
        from PIL import ImageGrab
        import pyautogui

        if window_title:
            win = window_manager.find_window_simple(window_title)
            if win:
                window_manager.focus_window(win)
                time.sleep(0.2)
                info = win.element_info
                rect = info.rectangle
                if rect:
                    bbox = (rect.left, rect.top, rect.right, rect.bottom)
                    img = ImageGrab.grab(bbox=bbox)
                else:
                    img = ImageGrab.grab()
            else:
                img = ImageGrab.grab()
        else:
            img = ImageGrab.grab()

        result = {
            "status": "success",
            "width": img.width,
            "height": img.height,
        }

        if save_path:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            img.save(save_path)
            result["saved_to"] = os.path.abspath(save_path)

        if return_base64:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            result["base64"] = img_b64

        return result
    except Exception as e:
        return {"status": "failure", "details": f"Screenshot failed: {str(e)}"}


# ── Complete Tool Registry ───────────────────────────────────────────────────
ALL_TOOLS: List[ToolDefinition] = [
    ToolDefinition(
        name="aura_execute_prompt",
        description="Execute a natural language desktop or browser automation goal using AURA's agent routing pipeline.",
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The natural language instruction (e.g., 'Open Notepad, write Meeting Summary, and save as summary.txt').",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, generates and returns the execution plan without running it on the desktop.",
                    "default": False,
                },
            },
            "required": ["prompt"],
        },
        handler=handle_execute_prompt,
    ),
    ToolDefinition(
        name="aura_list_agents",
        description="List all available AURA automation agents, their capabilities, supported actions, and running status.",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=handle_list_agents,
    ),
    ToolDefinition(
        name="aura_get_agent_info",
        description="Get detailed capabilities, parameter schemas, and UI map status for a specific AURA agent.",
        input_schema={
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent (e.g. 'notepad', 'browser').",
                },
            },
            "required": ["agent_name"],
        },
        handler=handle_get_agent_info,
    ),
    ToolDefinition(
        name="aura_execute_agent_action",
        description="Directly execute a specific action on a designated AURA agent (e.g. notepad.type, notepad.save_as).",
        input_schema={
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "The target agent name ('notepad', 'browser', etc.).",
                },
                "action": {
                    "type": "string",
                    "description": "The action to execute (e.g., 'open', 'type', 'save', 'save_as', 'close', 'create_service_request').",
                },
                "params": {
                    "type": "object",
                    "description": "Dictionary of parameters for the action (e.g. {'text': 'Hello World'}).",
                    "default": {},
                },
            },
            "required": ["agent_name", "action"],
        },
        handler=handle_execute_agent_action,
    ),
    ToolDefinition(
        name="aura_list_windows",
        description="List open top-level application windows on the Windows desktop.",
        input_schema={
            "type": "object",
            "properties": {
                "title_filter": {
                    "type": "string",
                    "description": "Optional substring to filter window titles.",
                },
                "visible_only": {
                    "type": "boolean",
                    "description": "If true, only lists visible windows with titles.",
                    "default": True,
                },
            },
        },
        handler=handle_list_windows,
    ),
    ToolDefinition(
        name="aura_focus_window",
        description="Bring a target application window to the foreground and set keyboard focus.",
        input_schema={
            "type": "object",
            "properties": {
                "title_contains": {
                    "type": "string",
                    "description": "Substring of the window title to search for.",
                },
                "class_name": {
                    "type": "string",
                    "description": "Optional window class name to match.",
                },
            },
        },
        handler=handle_focus_window,
    ),
    ToolDefinition(
        name="aura_launch_app",
        description="Launch an application executable and wait for its window to appear.",
        input_schema={
            "type": "object",
            "properties": {
                "executable": {
                    "type": "string",
                    "description": "Path or executable name (e.g., 'notepad.exe', 'calc.exe').",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional command line arguments.",
                },
                "wait_title": {
                    "type": "string",
                    "description": "Expected window title substring to wait for.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Max seconds to wait for the window.",
                    "default": 10.0,
                },
            },
            "required": ["executable"],
        },
        handler=handle_launch_app,
    ),
    ToolDefinition(
        name="aura_close_window",
        description="Gracefully close an application window.",
        input_schema={
            "type": "object",
            "properties": {
                "title_contains": {
                    "type": "string",
                    "description": "Substring of the window title.",
                },
                "class_name": {
                    "type": "string",
                    "description": "Optional class name of the window.",
                },
            },
        },
        handler=handle_close_window,
    ),
    ToolDefinition(
        name="aura_inspect_window",
        description="Traverse the live UI Automation (UIA) tree of a window to inspect element hierarchy, names, types, and automation IDs.",
        input_schema={
            "type": "object",
            "properties": {
                "title_contains": {
                    "type": "string",
                    "description": "Substring of the window title to inspect.",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum tree depth to traverse.",
                    "default": 4,
                },
            },
            "required": ["title_contains"],
        },
        handler=handle_inspect_window,
    ),
    ToolDefinition(
        name="aura_find_element",
        description="Search for a specific UI element inside an active application window matching multi-property criteria.",
        input_schema={
            "type": "object",
            "properties": {
                "window_title": {
                    "type": "string",
                    "description": "Window title to search inside.",
                },
                "name": {
                    "type": "string",
                    "description": "Element name or label.",
                },
                "control_type": {
                    "type": "string",
                    "description": "Control type (e.g., 'Edit', 'Button', 'MenuItem', 'Document').",
                },
                "automation_id": {
                    "type": "string",
                    "description": "UIA AutomationId.",
                },
                "class_name": {
                    "type": "string",
                    "description": "Window class name.",
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum match confidence score (0.0 to 1.0).",
                    "default": 0.5,
                },
            },
            "required": ["window_title"],
        },
        handler=handle_find_element,
    ),
    ToolDefinition(
        name="aura_send_input",
        description="Send safe keyboard shortcuts, text (via clipboard paste to avoid repeat bugs), or key sequences.",
        input_schema={
            "type": "object",
            "properties": {
                "input_type": {
                    "type": "string",
                    "enum": ["text", "hotkey", "key_sequence"],
                    "description": "Type of input: 'text' (types text safely), 'hotkey' (e.g. 'ctrl+s'), or 'key_sequence' (e.g. 'enter').",
                },
                "value": {
                    "type": "string",
                    "description": "The string value or shortcut key to send.",
                },
                "window_title": {
                    "type": "string",
                    "description": "Optional window title to focus before sending input.",
                },
            },
            "required": ["input_type", "value"],
        },
        handler=handle_send_input,
    ),
    ToolDefinition(
        name="aura_verify_state",
        description="Verify post-action desktop state (window exists/closed, text content present, element visible).",
        input_schema={
            "type": "object",
            "properties": {
                "verification_type": {
                    "type": "string",
                    "enum": ["window_exists", "window_closed", "text_contains", "element_exists"],
                    "description": "The verification check type.",
                },
                "expected_value": {
                    "type": "string",
                    "description": "The expected string value (e.g., window title substring, text substring, element name).",
                },
                "target_window": {
                    "type": "string",
                    "description": "Target window title for text or element verification.",
                },
            },
            "required": ["verification_type", "expected_value"],
        },
        handler=handle_verify_state,
    ),
    ToolDefinition(
        name="aura_get_app_map",
        description="Get the loaded UI App Map JSON definition for an application (from app_maps/).",
        input_schema={
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Application name (e.g. 'notepad', 'browser').",
                },
            },
            "required": ["app_name"],
        },
        handler=handle_get_app_map,
    ),
    ToolDefinition(
        name="aura_take_screenshot",
        description="Capture a screenshot of a specific window or the entire desktop.",
        input_schema={
            "type": "object",
            "properties": {
                "window_title": {
                    "type": "string",
                    "description": "Optional window title substring to capture only that window.",
                },
                "save_path": {
                    "type": "string",
                    "description": "Optional file path to save the screenshot PNG.",
                },
                "return_base64": {
                    "type": "boolean",
                    "description": "If true, returns the screenshot as a base64 string.",
                    "default": True,
                },
            },
        },
        handler=handle_take_screenshot,
    ),
]


def get_tool(name: str) -> Optional[ToolDefinition]:
    """Find a tool by name."""
    for tool in ALL_TOOLS:
        if tool.name == name:
            return tool
    return None
