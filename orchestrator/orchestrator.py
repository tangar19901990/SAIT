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
            {
                "role": "system",
                "content": "You are TOP SECRET AI. Plan tasks, use tools carefully, verify results, and stop when the goal is complete. When a tool result gives you enough information to continue, continue the task yourself instead of asking the user what to do next. Preserve the user's original goal throughout the entire task.",
            },
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

            # Keep the model's function-call messages in the conversation.
            # This is essential for OpenRouter, which cannot use
            # previous_response_id for multi-step Responses API turns.
            output_items = response.get("output_items", [])
            if output_items:
                messages.extend(output_items)

            for call in calls:
                name = call["name"]
                arguments = call.get("arguments", {})
                try:
                    result = self.tools.call(name, **arguments)
                except Exception as exc:
                    result = {"error": str(exc)}

                state.history.append({
                    "action": name,
                    "arguments": arguments,
                    "result": result,
                })
                messages.append({
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": str(result),
                })

            # The next model turn receives the complete accumulated context,
            # not only the latest tool result.
            if self.runtime.provider.is_openrouter:
                previous_response_id = None

        state.status = "max_steps"
        return state
