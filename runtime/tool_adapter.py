from typing import Any


class ToolAdapter:
    """Expose registered tools as model-readable schemas and dispatch calls."""

    def __init__(self, registry):
        self.registry = registry

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item["name"],
                "description": item["description"],
            }
            for item in self.registry.describe()
        ]

    def call(self, name: str, **arguments):
        return self.registry.get(name)(**arguments)
