from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionState:
    goal: str
    history: list[dict[str, Any]] = field(default_factory=list)
    status: str = "running"


class Orchestrator:
    """Coordinates an AI provider with registered tools."""

    def __init__(self, runtime, tool_adapter, max_steps: int = 30, max_repeated_calls: int = 3):
        self.runtime = runtime
        self.tools = tool_adapter
        self.max_steps = max_steps
        self.max_repeated_calls = max_repeated_calls

    def _system_prompt(self, goal: str) -> str:
        research_words = (
            "знайди", "пошукай", "найдешев", "порівняй", "ціна", "пропозиці",
            "оголош", "ринок", "інтернет", "find", "search", "cheapest",
            "compare", "price", "listing", "market", "research"
        )
        is_research = any(word in goal.lower() for word in research_words)

        prompt = (
            "You are TOP SECRET AI, a local computer-use agent. "
            "Plan tasks, use tools carefully, verify results, and stop only when the user's goal is complete. "
            "When a tool result gives you enough information to continue, continue the task yourself instead of asking the user what to do next. "
            "Preserve the user's original goal throughout the entire task. "
            "Never claim that you performed an action unless a tool actually performed it. "
            "Never invent URLs, prices, product names, availability, page contents, or other facts. "
            "When browser tools are available, use them for web tasks instead of saying that you cannot access the internet. "
            "After each browser action, inspect the resulting page before deciding the next action. "
            "Keep track of the exact requested subject, search query, and current page so you do not switch to an unrelated task. "
            "If a tool fails, inspect the error and adapt instead of repeating the exact same failed call. "
        )

        if is_research:
            prompt += (
                "\nRESEARCH MODE IS ACTIVE. Treat every factual result as evidence that must be verified from the actual page. "
                "For each candidate, open the specific source page and verify the exact item, exact size/specification, price, condition, and direct URL when those fields are requested. "
                "Do not treat a search-result snippet or a category page as proof of a specific offer. "
                "If a requested field is missing or cannot be verified, write 'не підтверджено' rather than guessing. "
                "Do not call something the cheapest unless you actually compared enough verified offers to support that claim. "
                "Prefer direct listing/product URLs over homepages. "
                "Before the final answer, re-check that every row in a comparison table is supported by a source actually visited during this task. "
                "For research results, clearly separate verified facts from assumptions and include the source URL for each result. "
            )

        return prompt

    @staticmethod
    def _short_result(result: Any, limit: int = 20000) -> str:
        text = str(result)
        if len(text) <= limit:
            return text
        return text[:limit] + "\n[tool output truncated by SAIT]"

    def run(self, goal: str) -> ExecutionState:
        state = ExecutionState(goal=goal)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt(goal)},
            {"role": "user", "content": goal},
        ]
        tool_schemas = self.tools.schemas()
        recent_calls: list[str] = []

        for step in range(self.max_steps):
            response = self.runtime.run(
                messages,
                tools=tool_schemas,
                previous_response_id=None,
            )
            calls = response.get("function_calls", [])

            if not calls:
                output = response.get("text") or "Задача завершена."
                state.history.append({"action": "finish", "output": output})
                state.status = "completed"
                return state

            output_items = response.get("output_items", [])
            if output_items:
                messages.extend(output_items)

            for call in calls:
                name = call.get("name", "")
                arguments = call.get("arguments", {}) or {}
                call_key = f"{name}:{arguments}"
                recent_calls.append(call_key)
                recent_calls = recent_calls[-self.max_repeated_calls:]

                if len(recent_calls) == self.max_repeated_calls and len(set(recent_calls)) == 1:
                    state.history.append({
                        "action": "guard",
                        "output": f"Stopped repeated tool call: {name}",
                    })
                    state.status = "stopped_repeated_tool_call"
                    return state

                try:
                    result = self.tools.call(name, **arguments)
                except Exception as exc:
                    result = {"error": f"{type(exc).__name__}: {exc}"}

                result_text = self._short_result(result)
                state.history.append({
                    "action": name,
                    "arguments": arguments,
                    "result": result_text,
                })
                messages.append({
                    "type": "function_call_output",
                    "name": name,
                    "call_id": call.get("call_id", f"call-{step}"),
                    "output": result_text,
                })

        state.status = f"max_steps:{self.max_steps}"
        state.history.append({
            "action": "guard",
            "output": f"Stopped after {self.max_steps} steps without completion.",
        })
        return state
