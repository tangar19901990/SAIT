from dataclasses import dataclass
from typing import Any, Protocol


class ModelProvider(Protocol):
    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]: ...


@dataclass
class RuntimeConfig:
    model: str = "default"
    max_tokens: int = 8192
    temperature: float = 0.2


class AIRuntime:
    """Provider-neutral runtime facade.

    The concrete provider is injected, so OpenAI, Anthropic, OpenRouter or
    another compatible backend can be swapped without changing the agent core.
    """

    def __init__(self, provider: ModelProvider, config: RuntimeConfig | None = None):
        self.provider = provider
        self.config = config or RuntimeConfig()

    def run(self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None):
        return self.provider.complete(messages, tools=tools)
