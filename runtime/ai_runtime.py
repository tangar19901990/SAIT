from dataclasses import dataclass
from typing import Any, Protocol


class ModelProvider(Protocol):
    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        previous_response_id: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass
class RuntimeConfig:
    model: str = "default"
    max_tokens: int = 8192
    temperature: float = 0.2


class AIRuntime:
    """Provider-neutral runtime facade."""

    def __init__(self, provider: ModelProvider, config: RuntimeConfig | None = None):
        self.provider = provider
        self.config = config or RuntimeConfig()

    def run(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        previous_response_id: str | None = None,
    ):
        return self.provider.complete(
            messages,
            tools=tools,
            previous_response_id=previous_response_id,
        )
