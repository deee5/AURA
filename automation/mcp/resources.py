"""
AURA MCP Resources — Real-time dynamic resources providing system status, agents, active windows, and UI app maps.
"""

from __future__ import annotations
import json
import os
import platform
import sys
import time
from typing import Any, Dict, List, Optional

from automation.mcp.schemas import ResourceDefinition
from automation.core.registry import registry
from automation.core import window_manager
from automation.core.app_map import load_app_map


def _get_system_status(_uri: str) -> str:
    """Return real-time AURA system health and runtime metadata."""
    agents = registry.get_all_agents()
    status_data = {
        "status": "online",
        "server": "aura-mcp",
        "version": "1.0.0",
        "platform": platform.platform(),
        "python_version": sys.version,
        "registered_agents": list(agents.keys()),
        "agent_count": len(agents),
        "timestamp": time.time(),
        "features": {
            "window_management": True,
            "safe_clipboard_input": True,
            "multi_property_element_finder": True,
            "post_action_verification": True,
            "offline_rule_planner": True,
            "gemini_llm_orchestrator": bool(os.environ.get("GEMINI_API_KEY")),
        },
    }
    return json.dumps(status_data, indent=2)


def _get_agents_resource(_uri: str) -> str:
    """Return list of all registered agents and their capabilities."""
    all_agents = registry.get_all_agents()
    result = {}
    for name, agent in all_agents.items():
        try:
            caps = agent.get_capabilities()
        except Exception:
            caps = {}
        result[name] = {
            "name": name,
            "app_name": getattr(agent, "app_name", name),
            "process_name": getattr(agent, "process_name", "unknown"),
            "is_running": agent.is_running(),
            "capabilities": caps.get("actions", {}),
        }
    return json.dumps({"count": len(result), "agents": result}, indent=2)


def _get_single_agent_resource(uri: str) -> str:
    """Return details for a specific agent (aura://agents/{agent_name})."""
    agent_name = uri.split("/")[-1].lower()
    agent = registry.get_agent(agent_name)
    if not agent:
        return json.dumps({"error": f"Agent '{agent_name}' not found"}, indent=2)

    app_map = load_app_map(agent_name)
    data = {
        "name": agent_name,
        "app_name": getattr(agent, "app_name", agent_name),
        "process_name": getattr(agent, "process_name", "unknown"),
        "is_running": agent.is_running(),
        "capabilities": agent.get_capabilities(),
        "llm_prompt": agent.get_llm_capabilities(),
        "app_map": app_map.elements if app_map else None,
    }
    return json.dumps(data, indent=2)


def _get_open_windows_resource(_uri: str) -> str:
    """Return live list of open desktop windows."""
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        windows = []
        for win in desktop.windows():
            try:
                info = win.element_info
                name = (info.name or "").strip()
                if not name or not info.visible:
                    continue
                windows.append({
                    "title": name,
                    "class_name": info.class_name or "",
                    "process_id": info.process_id,
                    "handle": info.handle,
                })
            except Exception:
                continue
        return json.dumps({"count": len(windows), "windows": windows}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "windows": []}, indent=2)


def _get_app_maps_list_resource(_uri: str) -> str:
    """Return list of available UI App Maps."""
    maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app_maps")
    maps = []
    if os.path.exists(maps_dir):
        for f in os.listdir(maps_dir):
            if f.endswith(".json"):
                app_name = f[:-5]
                maps.append({
                    "app_name": app_name,
                    "filename": f,
                    "uri": f"aura://app-maps/{app_name}",
                })
    return json.dumps({"count": len(maps), "app_maps": maps}, indent=2)


def _get_single_app_map_resource(uri: str) -> str:
    """Return JSON content of a specific app map."""
    app_name = uri.split("/")[-1].lower()
    app_map = load_app_map(app_name)
    if not app_map:
        return json.dumps({"error": f"App map for '{app_name}' not found"}, indent=2)

    return json.dumps({
        "application": app_map.application,
        "version": app_map.version,
        "elements": app_map.elements,
    }, indent=2)


# ── Static & Dynamic Resource Registry ────────────────────────────────────────
STATIC_RESOURCES: List[ResourceDefinition] = [
    ResourceDefinition(
        uri="aura://system/status",
        name="AURA System Status",
        description="Real-time health, platform info, and registered agent count for AURA.",
        mime_type="application/json",
        handler=_get_system_status,
    ),
    ResourceDefinition(
        uri="aura://agents",
        name="Registered Agents",
        description="All loaded desktop and browser automation agents and their capabilities.",
        mime_type="application/json",
        handler=_get_agents_resource,
    ),
    ResourceDefinition(
        uri="aura://windows/open",
        name="Active Desktop Windows",
        description="Live list of visible top-level application windows currently running.",
        mime_type="application/json",
        handler=_get_open_windows_resource,
    ),
    ResourceDefinition(
        uri="aura://app-maps",
        name="UI App Maps Index",
        description="List of all UI element maps available in the app_maps/ directory.",
        mime_type="application/json",
        handler=_get_app_maps_list_resource,
    ),
]


def get_all_resources() -> List[ResourceDefinition]:
    """Return all resources including dynamically discovered ones."""
    resources = list(STATIC_RESOURCES)

    # Add dynamic resources for each registered agent
    for agent_name in registry.get_all_agents().keys():
        resources.append(
            ResourceDefinition(
                uri=f"aura://agents/{agent_name}",
                name=f"Agent: {agent_name}",
                description=f"Capabilities and configuration for '{agent_name}' agent.",
                mime_type="application/json",
                handler=_get_single_agent_resource,
            )
        )

    # Add dynamic resources for each app map
    maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app_maps")
    if os.path.exists(maps_dir):
        for f in os.listdir(maps_dir):
            if f.endswith(".json"):
                name = f[:-5]
                resources.append(
                    ResourceDefinition(
                        uri=f"aura://app-maps/{name}",
                        name=f"App Map: {name}",
                        description=f"UI element tree and selectors for '{name}'.",
                        mime_type="application/json",
                        handler=_get_single_app_map_resource,
                    )
                )

    return resources


def read_resource(uri: str) -> Optional[Dict[str, Any]]:
    """Read resource content by URI."""
    uri_clean = uri.strip()

    for res in get_all_resources():
        if res.uri == uri_clean:
            content = res.handler(uri_clean)
            return {
                "uri": res.uri,
                "mimeType": res.mime_type,
                "text": content if isinstance(content, str) else content.decode("utf-8"),
            }

    # Fallback pattern matches
    if uri_clean.startswith("aura://agents/"):
        return {
            "uri": uri_clean,
            "mimeType": "application/json",
            "text": _get_single_agent_resource(uri_clean),
        }

    if uri_clean.startswith("aura://app-maps/"):
        return {
            "uri": uri_clean,
            "mimeType": "application/json",
            "text": _get_single_app_map_resource(uri_clean),
        }

    return None
