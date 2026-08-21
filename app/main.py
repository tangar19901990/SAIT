import os
from pathlib import Path

from coding import CodingEngine, AutoCoder
from design import DesignEngine, DesignCodeBridge
from memory import TaskMemory
from orchestrator import Orchestrator
from runtime import AIRuntime
from tools.registry import ToolRegistry


class DemoProvider:
    """Placeholder provider for local smoke tests.

    Replace with a real provider adapter through SAIT_PROVIDER before production use.
    """

    def complete(self, messages, tools=None):
        return {"action": "finish", "output": "Runtime is connected. Configure a real AI provider."}


def build_app():
    workspace = Path(os.getenv("SAIT_WORKSPACE", "workspace")).resolve()
    coding = CodingEngine(str(workspace))
    registry = ToolRegistry()
    registry.register("read_file", "Read a project file", coding.read_file)
    registry.register("write_file", "Write a project file", coding.write_file)
    registry.register("list_files", "List project files", lambda: coding.list_files())
    registry.register("run_command", "Run an explicit command in the workspace", coding.run)

    runtime = AIRuntime(DemoProvider())
    orchestrator = Orchestrator(runtime, __import__("runtime.tool_adapter", fromlist=["ToolAdapter"]).ToolAdapter(registry))
    memory = TaskMemory()
    return orchestrator, memory


def main():
    orchestrator, memory = build_app()
    print("TOP SECRET AI - local runtime")
    print("Type 'exit' to quit.")
    while True:
        try:
            goal = input("\nYOU > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if goal.lower() in {"exit", "quit"}:
            break
        if not goal:
            continue
        state = orchestrator.run(goal)
        summary = state.history[-1].get("output", state.status) if state.history else state.status
        memory.remember(goal, state.status, str(summary))
        print(f"AI  > {summary}")


if __name__ == "__main__":
    main()
