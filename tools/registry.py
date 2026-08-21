from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    parameters: dict[str, Any]
    requires_approval: bool = False


class ToolRegistry:
    """Central registry for discoverable tools and approval requirements."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("Tool name cannot be empty")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description,
             "parameters": t.parameters, "requires_approval": t.requires_approval}
            for t in self._tools.values()
        ]
