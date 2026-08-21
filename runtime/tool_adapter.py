from typing import Any


class ToolAdapter:
    """Expose registry tools as Responses API function tools and dispatch them."""

    def __init__(self, registry):
        self.registry = registry

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": item["name"],
                "description": item["description"],
                "parameters": item.get("parameters", {"type": "object", "properties": {}}),
                "strict": True,
            }
            for item in self.registry.describe()
        ]

    def call(self, name: str, **arguments):
        tool = self.registry.get(name)
        return tool.handler(**arguments)
