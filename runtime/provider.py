from typing import Any, Protocol


class AIProvider(Protocol):
    def decide(self, *, task: str, history: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Return an agent decision: {action, arguments} or {action: finish, output}."""
        ...


class MissingProvider:
    """Safe placeholder until a real provider adapter is configured."""

    def decide(self, *, task: str, history: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "action": "finish",
            "output": "AI provider is not configured yet.",
        }
