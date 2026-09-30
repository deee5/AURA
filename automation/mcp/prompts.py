"""
AURA MCP Prompts — Intelligent workflow prompt templates for desktop automation,
agent creation, UI tree debugging, and safety verification.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from automation.mcp.schemas import PromptArgument, PromptDefinition
from automation.core.registry import registry


def _handle_orchestrate_task(goal: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate prompt for orchestrating complex desktop tasks."""
    agents = registry.get_all_agents()
    capabilities_text = ""
    for name, agent in agents.items():
        capabilities_text += f"\n--- Agent: {name} ({getattr(agent, 'app_name', name)}) ---\n"
        capabilities_text += agent.get_llm_capabilities().strip() + "\n"

    system_prompt = f"""You are the AURA Desktop Automation Specialist.
Your objective is to accomplish the user's desktop goal by coordinating AURA agents and low-level tools with precision.

Available Agents:
{capabilities_text}

Rules:
1. Break down the user's goal into atomic, sequential steps.
2. Before performing actions on an app, ensure it is opened and focused (e.g., `aura_focus_window` or agent `open`).
3. For typing, use AURA's clipboard-safe typing to avoid repeat-key bugs.
4. Always verify state changes after critical actions (e.g. `aura_verify_state`).
5. If an action fails, inspect the window using `aura_inspect_window` to diagnose the UI tree.
"""
    messages = [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"{system_prompt}\n\nTask Goal: {goal}\nAdditional Context: {context or 'None'}\n\nPlease plan and execute the required actions.",
            },
        }
    ]
    return messages


def _handle_build_new_agent(
    app_name: str, executable: str, actions_needed: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Generate prompt for scaffolding a new AURA automation agent."""
    prompt_text = f"""You are an Expert Architect for the AURA Automation System.
You need to create a new application agent for: '{app_name}' (Executable: '{executable}').
Desired actions: {actions_needed or 'open, navigate, type, click, save, close'}

Follow the 3-step AURA Plugin Blueprint:
1. Create `app_maps/{app_name.lower()}.json` defining logical UI elements and their UIA identifiers (`name`, `automation_id`, `control_type`, `class_name`).
2. Create `automation/agents/{app_name.lower()}_agent.py` inheriting from `BaseAgent`.
3. Implement `get_capabilities()`, `get_llm_capabilities()`, `resolve()`, `execute()`, and `verify()`.

Provide the full, production-ready code for both files following AURA best practices (safe typing, window focusing, error wrapping).
"""
    return [
        {
            "role": "user",
            "content": {"type": "text", "text": prompt_text},
        }
    ]


def _handle_debug_ui_tree(
    window_title: str, target_element: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Generate prompt for debugging UI tree locators."""
    prompt_text = f"""You are debugging a Windows UI Automation locator issue in AURA.
Target Window: '{window_title}'
Target Element to locate: '{target_element or 'Any interactable element'}'

Instructions:
1. Use `aura_inspect_window` with `title_contains='{window_title}'` to retrieve the active UIA accessibility tree.
2. Search for the target element's `name`, `control_type`, `automation_id`, and `class_name`.
3. If AutomationId is dynamic or missing, provide multi-property fallback criteria (Tier 1 App Map + Tier 2 heuristic search).
4. Output the optimal entry to add to the app map JSON.
"""
    return [
        {
            "role": "user",
            "content": {"type": "text", "text": prompt_text},
        }
    ]


def _handle_safety_review(proposed_actions: str) -> List[Dict[str, Any]]:
    """Generate prompt for safety risk review."""
    prompt_text = f"""You are the AURA Safety Gate Auditor.
Analyze the following proposed action sequence for potential risks:

Proposed Actions:
{proposed_actions}

Audit Checklist:
- Does any action permanently delete or overwrite files?
- Does any action submit financial, personal, or institutional data?
- Does any action terminate processes without saving work?
- Are all parameters bounded and sanitized?

Provide a verdict: 'APPROVED' or 'REQUIRES_USER_CONFIRMATION' with specific rationale.
"""
    return [
        {
            "role": "user",
            "content": {"type": "text", "text": prompt_text},
        }
    ]


# ── Prompt Registry ──────────────────────────────────────────────────────────
ALL_PROMPTS: List[PromptDefinition] = [
    PromptDefinition(
        name="aura_orchestrate_task",
        description="Step-by-step guidance for an LLM to plan, verify, and execute complex desktop automation tasks with AURA.",
        arguments=[
            PromptArgument(name="goal", description="The automation goal to achieve.", required=True),
            PromptArgument(name="context", description="Optional background details or constraints.", required=False),
        ],
        handler=_handle_orchestrate_task,
    ),
    PromptDefinition(
        name="aura_build_new_agent",
        description="Scaffold a new modular application agent and UI app map following AURA's plugin architecture.",
        arguments=[
            PromptArgument(name="app_name", description="Name of the application (e.g. 'calculator', 'vscode', 'excel').", required=True),
            PromptArgument(name="executable", description="Executable name or path (e.g. 'calc.exe', 'code.exe').", required=True),
            PromptArgument(name="actions_needed", description="Comma-separated list of actions to support.", required=False),
        ],
        handler=_handle_build_new_agent,
    ),
    PromptDefinition(
        name="aura_debug_ui_tree",
        description="Inspect and debug UI element selectors and accessibility tree for Windows applications.",
        arguments=[
            PromptArgument(name="window_title", description="Window title to inspect.", required=True),
            PromptArgument(name="target_element", description="Name or role of the element you are trying to locate.", required=False),
        ],
        handler=_handle_debug_ui_tree,
    ),
    PromptDefinition(
        name="aura_safety_review",
        description="Audit an automation sequence for destructive actions before executing on the user's machine.",
        arguments=[
            PromptArgument(name="proposed_actions", description="JSON or text description of actions to review.", required=True),
        ],
        handler=_handle_safety_review,
    ),
]


def get_prompt(name: str) -> Optional[PromptDefinition]:
    """Find a prompt definition by name."""
    for prompt in ALL_PROMPTS:
        if prompt.name == name:
            return prompt
    return None
