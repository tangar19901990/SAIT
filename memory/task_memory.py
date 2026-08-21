from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass
class MemoryRecord:
    goal: str
    status: str
    summary: str
    created_at: str


class TaskMemory:
    """Small local JSONL memory for completed agent tasks."""

    def __init__(self, path: str = "data/task_memory.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def remember(self, goal: str, status: str, summary: str):
        record = MemoryRecord(
            goal=goal,
            status=status,
            summary=summary,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def recent(self, limit: int = 20) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:]]
