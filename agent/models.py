from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ToolResult:
    ok: bool
    output: Any = None
    error: str | None = None


@dataclass
class Task:
    goal: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    id: str
    description: str
    tool: str | None = None
    risk: Risk = Risk.LOW
    requires_approval: bool = False


@dataclass
class AgentPlan:
    goal: str
    steps: list[PlanStep]
