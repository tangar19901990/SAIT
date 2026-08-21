from pathlib import Path
import subprocess


def read_file(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    return {"path": str(p), "content": p.read_text(encoding="utf-8")}


def write_file(path: str, content: str) -> dict:
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "bytes": p.stat().st_size}


def run_command(command: str, cwd: str | None = None) -> dict:
    completed = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120)
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
