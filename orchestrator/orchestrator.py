from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ExecutionState:
    goal: str
    history: list[dict[str, Any]] = field(default_factory=list)
    status: str = "running"


class Orchestrator:
    """Coordinates planning and tool execution without owning any AI provider."""

    def __init__(self, runtime, tool_adapter, max_steps: int = 30):
        self.runtime = runtime
        self.tools = tool_adapter
        self.max_steps = max_steps

    def run(self, goal: str) -> ExecutionState:
        state = ExecutionState(goal=goal)
        messages = [
            {"role": "system", "content": "You are TOP SECRET AI. Plan tasks, use tools carefully, verify results, and stop when the goal is complete."},
            {"role": "user", "content": goal},
        ]

        for _ in range(self.max_steps):
            response = self.runtime.run(messages, tools=self.tools.schemas())
            action = response.get("action", "finish")
            arguments = response.get("arguments", {})

            if action == "finish":
                state.history.append({"action": "finish", "output": response.get("output")})
                state.status = "completed"
                return state

            try:
                result = self.tools.call(action, **arguments)
            except Exception as exc:
                result = {"error": str(exc)}

            state.history.append({"action": action, "arguments": arguments, "result": result})
            messages.append({"role": "assistant", "content": str(response)})
            messages.append({"role": "tool", "content": str(result)})

        state.status = "max_steps"
        return state
