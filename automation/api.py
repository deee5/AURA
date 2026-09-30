import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from automation.core.llm_orchestrator import LLMOrchestrator
from automation.core.registry import registry

app = Flask(__name__)
# Enable CORS so the React frontend can talk to us
CORS(app)

# Initialize singletons
try:
    planner = LLMOrchestrator()
except Exception as e:
    print(f"LLM Orchestrator offline (API key not set or package missing): {e}")
    planner = None

from automation.core.planner import SimplePlanner
from automation.mcp.server import MCPServer
from automation.mcp.tools import ALL_TOOLS, get_tool
from automation.mcp.resources import get_all_resources, read_resource
from automation.mcp.prompts import ALL_PROMPTS, get_prompt

mcp_server = MCPServer()

# ── Standard AURA Execution API ───────────────────────────────────────────────

@app.route("/api/execute", methods=["POST"])
def execute_prompt():
    data = request.json
    if not data or "prompt" not in data:
        return jsonify({"error": "No prompt provided"}), 400

    prompt = data["prompt"]
    print(f"\n[API] Received prompt: {prompt}")

    # 1. Parse actions via LLM or SimplePlanner fallback
    plan_result = None
    if planner:
        try:
            plan_result = planner.plan(prompt)
        except Exception as e:
            print(f"[API] LLM planning failed, falling back to rule planner: {e}")

    if not plan_result or (not plan_result.get("actions") and not plan_result.get("message")):
        rule_planner = SimplePlanner()
        actions = rule_planner.plan(prompt)
        plan_result = {
            "message": f"Planned {len(actions)} step(s) via offline rule planner.",
            "actions": actions,
        }

    actions = plan_result.get("actions", [])
    message = plan_result.get("message", "")

    # We still allow execution if actions exist.
    # If no actions but we have a message, it's a conversational response!
    if not actions and not message:
        return jsonify({
            "status": "error",
            "message": "Could not understand the command.",
            "steps": []
        })

    # 2. Execute actions
    steps_results = []
    task_status = "COMPLETED"

    for idx, act in enumerate(actions, 1):
        agent_name = act.get("agent", "unknown")
        action_name = act.get("action")
        params = act.get("params", {})

        print(f"  [Step {idx}] {agent_name} -> {action_name} {params}")

        agent = registry.get_agent(agent_name)
        if agent:
            result = agent.execute(action_name, params)
        else:
            result = {
                "status": "failure",
                "action": action_name,
                "details": f"Unknown agent: {agent_name}",
                "duration_ms": 0
            }

        steps_results.append({
            "step": idx,
            "agent": agent_name,
            "action": action_name,
            "params": params,
            "status": result.get("status"),
            "details": result.get("details", ""),
            "duration_ms": result.get("duration_ms", 0)
        })

        if result.get("status") == "failure":
            task_status = "FAILED"
            break

    return jsonify({
        "status": task_status,
        "prompt": prompt,
        "steps": steps_results,
        "message": message
    })


# ── MCP (Model Context Protocol) Endpoints ────────────────────────────────────

@app.route("/mcp", methods=["POST"])
def mcp_jsonrpc_endpoint():
    """Direct JSON-RPC 2.0 endpoint for MCP clients."""
    payload = request.get_data(as_text=True)
    response = mcp_server.process_message(payload)
    if response:
        return app.response_class(response, mimetype="application/json")
    return jsonify({})


@app.route("/mcp/tools", methods=["GET"])
def mcp_list_tools():
    """List all available MCP tools."""
    return jsonify(mcp_server.handle_tools_list())


@app.route("/mcp/resources", methods=["GET"])
def mcp_list_resources():
    """List all available MCP resources."""
    return jsonify(mcp_server.handle_resources_list())


@app.route("/mcp/prompts", methods=["GET"])
def mcp_list_prompts():
    """List all available MCP prompts."""
    return jsonify(mcp_server.handle_prompts_list())


@app.route("/api/mcp/call", methods=["POST"])
def mcp_call_tool_rest():
    """REST wrapper to call any MCP tool directly: {"name": "...", "arguments": {...}}."""
    data = request.json or {}
    tool_name = data.get("name") or data.get("tool")
    arguments = data.get("arguments") or data.get("params") or {}

    if not tool_name:
        return jsonify({"error": "Missing 'name' parameter for tool."}), 400

    tool = get_tool(tool_name)
    if not tool:
        return jsonify({"error": f"Tool '{tool_name}' not found."}), 404

    try:
        result = tool.handler(**arguments)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    print("==================================================")
    print(" AURA Backend & MCP API Started on Port 5000")
    print(" REST API: http://127.0.0.1:5000/api/execute")
    print(" MCP JSON-RPC: http://127.0.0.1:5000/mcp")
    print(" MCP Tools: http://127.0.0.1:5000/mcp/tools")
    print("==================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
