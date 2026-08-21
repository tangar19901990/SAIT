from dataclasses import dataclass
from typing import Callable

from .coding_engine import CodingEngine, CommandResult


@dataclass
class CodingSession:
    goal: str
    attempts: int = 0
    history: list[dict] | None = None

    def __post_init__(self):
        self.history = [] if self.history is None else self.history


class AutoCoder:
    """Execution/recovery loop for coding tasks.

    A planner supplies actions. The engine executes only explicit workspace
    operations. The planner can inspect command output and decide whether to
    edit files, rerun tests, or finish.
    """

    def __init__(self, engine: CodingEngine, planner: Callable):
        self.engine = engine
        self.planner = planner

    def run(self, goal: str, max_attempts: int = 8) -> CodingSession:
        session = CodingSession(goal)

        for attempt in range(1, max_attempts + 1):
            session.attempts = attempt
            decision = self.planner(goal, session.history)
            action = decision.get("action", "finish")

            if action == "finish":
                session.history.append({"action": action, "result": decision.get("output")})
                return session

            if action == "write_file":
                result = self.engine.write_file(
                    decision["path"], decision.get("content", "")
                )
            elif action == "read_file":
                result = self.engine.read_file(decision["path"])
            elif action == "list_files":
                result = self.engine.list_files()
            elif action == "run":
                command = decision["command"]
                result = self.engine.run(command, decision.get("timeout", 120))
                if isinstance(result, CommandResult):
                    result = {
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
            else:
                raise ValueError(f"Unknown coding action: {action}")

            session.history.append({"action": action, "result": result})

        return session
