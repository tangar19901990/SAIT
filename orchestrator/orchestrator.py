from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionState:
    goal: str
    history: list[dict[str, Any]] = field(default_factory=list)
    status: str = "running"


class Orchestrator:
    """Coordinates an AI provider with registered tools."""

    def __init__(self, runtime, tool_adapter, max_steps: int = 30):
        self.runtime = runtime
        self.tools = tool_adapter
        self.max_steps = max_steps

    def run(self, goal: str) -> ExecutionState:
        state = ExecutionState(goal=goal)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": "You are TOP SECRET AI. Plan tasks, use tools carefully, verify results, and stop when the goal is complete."},
            {"role": "user", "content": goal},
        ]
        previous_response_id = None

        for _ in range(self.max_steps):
            response = self.runtime.run(
                messages,
                tools=self.tools.schemas(),
                previous_response_id=previous_response_id,
            )
            previous_response_id = response.get("response_id")
            calls = response.get("function_calls", [])

            if not calls:
                output = response.get("text") or "Задача завершена."
                state.history.append({"action": "finish", "output": output})
                state.status = "completed"
                return state

            tool_outputs = []
            for call in calls:
                name = call["name"]
                arguments = call.get("arguments", {})
                try:
                    result = self.tools.call(name, **arguments)
                except Exception as exc:
                    result = {"error": str(exc)}

                state.history.append({"action": name, "arguments": arguments, "result": result})
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": str(result),
                })

            messages = tool_outputs

        state.status = "max_steps"
        return state
