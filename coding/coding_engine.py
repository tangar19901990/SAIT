from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CodingEngine:
    """Safe-ish local coding primitives for the agent.

    The engine is intentionally explicit: it can read/write project files and
    run commands inside a selected workspace. Higher-level policy decides which
    commands require user confirmation.
    """

    def __init__(self, workspace: str):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _path(self, relative_path: str) -> Path:
        target = (self.workspace / relative_path).resolve()
        if self.workspace != target and self.workspace not in target.parents:
            raise ValueError("Path escapes the coding workspace")
        return target

    def read_file(self, relative_path: str) -> str:
        return self._path(relative_path).read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> str:
        target = self._path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def run(self, command: list[str], timeout: int = 120) -> CommandResult:
        result = subprocess.run(
            command,
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return CommandResult(result.returncode, result.stdout, result.stderr)

    def list_files(self) -> list[str]:
        return [str(p.relative_to(self.workspace)) for p in self.workspace.rglob("*") if p.is_file()]
