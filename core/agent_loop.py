from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AgentTask:
    goal: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    status: str
    output: Any = None
    steps: list[str] = field(default_factory=list)


class AgentLoop:
    """Minimal tool-using agent loop.

    The model/planner is deliberately injected. This keeps the core independent
    from any single AI provider and lets us add routing later.
    """

    def __init__(self, planner: Callable[[AgentTask, list[dict]], dict], tools: dict[str, Callable]):
        self.planner = planner
        self.tools = tools

    def run(self, task: AgentTask, max_steps: int = 20) -> AgentResult:
        history: list[dict] = []
        steps: list[str] = []

        for _ in range(max_steps):
            decision = self.planner(task, history)
            action = decision.get("action", "finish")

            if action == "finish":
                return AgentResult("completed", decision.get("output"), steps)

            tool = self.tools.get(action)
            if tool is None:
                return AgentResult("error", f"Unknown tool: {action}", steps)

            arguments = decision.get("arguments", {})
            steps.append(f"{action}({arguments})")
            try:
                result = tool(**arguments)
            except Exception as exc:
                result = {"error": str(exc)}

            history.append({"action": action, "arguments": arguments, "result": result})

        return AgentResult("stopped", "Maximum agent steps reached", steps)
