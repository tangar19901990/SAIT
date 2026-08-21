from copy import deepcopy
from typing import Any


class ToolAdapter:
    """Expose registry tools as Responses API function tools and dispatch them."""

    def __init__(self, registry):
        self.registry = registry

    @staticmethod
    def _strict_schema(parameters: dict[str, Any]) -> dict[str, Any]:
        schema = deepcopy(parameters or {"type": "object", "properties": {}})
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        # OpenAI strict function schemas require every property to be required.
        properties = schema.get("properties") or {}
        schema["required"] = list(properties.keys())
        schema["additionalProperties"] = False
        return schema

    def schemas(self) -> list[dict[str, Any]]:
        result = []
        for item in self.registry.describe():
            result.append({
                "type": "function",
                "name": item["name"],
                "description": item["description"],
                "parameters": self._strict_schema(item.get("parameters")),
                "strict": True,
            })
        return result

    def call(self, name: str, **arguments):
        try:
            tool = self.registry.get(name)
        except KeyError as exc:
            raise ValueError(f"Unknown tool requested by AI: {name}") from exc
        if not isinstance(arguments, dict):
            raise TypeError(f"Tool arguments for {name} must be an object")
        return tool.handler(**arguments)
