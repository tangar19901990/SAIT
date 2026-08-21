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

    def run(self, goal: str) -> ExecutionState:
        state = ExecutionState(goal=goal)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt(goal)},
            {"role": "user", "content": goal},
        ]

        for step in range(self.max_steps):
            # Always send the complete local conversation history.
            # This avoids stale/cross-provider Responses API IDs when switching providers.
            response = self.runtime.run(
                messages,
                tools=self.tools.schemas(),
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
                # Keep the tool name so Gemini and Anthropic can construct
                # provider-specific tool-result messages correctly.
                messages.append({
                    "type": "function_call_output",
                    "name": name,
                    "call_id": call["call_id"],
                    "output": str(result),
                })

        state.status = f"max_steps:{self.max_steps}"
        return state
