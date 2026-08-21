from dataclasses import dataclass, field
from typing import Any


@dataclass
class DesignSpec:
    name: str
    goal: str
    platform: str = "web"
    style: str = "modern"
    viewport_targets: list[str] = field(default_factory=lambda: ["desktop", "tablet", "mobile"])
    tokens: dict[str, Any] = field(default_factory=dict)
    pages: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)


class DesignEngine:
    """Structured design planning layer for the agent."""

    def create_spec(self, name: str, goal: str, **kwargs) -> DesignSpec:
        return DesignSpec(name=name, goal=goal, **kwargs)

    def add_page(self, spec: DesignSpec, page: str):
        if page not in spec.pages:
            spec.pages.append(page)

    def add_component(self, spec: DesignSpec, component: str):
        if component not in spec.components:
            spec.components.append(component)

    def set_tokens(self, spec: DesignSpec, **tokens):
        spec.tokens.update(tokens)

    def export(self, spec: DesignSpec) -> dict[str, Any]:
        return {
            "name": spec.name,
            "goal": spec.goal,
            "platform": spec.platform,
            "style": spec.style,
            "viewport_targets": spec.viewport_targets,
            "tokens": spec.tokens,
            "pages": spec.pages,
            "components": spec.components,
        }
