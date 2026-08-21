import os
from pathlib import Path

from dotenv import load_dotenv

from browser import BrowserController, BrowserConfig
from coding import CodingEngine
from memory import TaskMemory
from orchestrator import Orchestrator
from runtime import AIRuntime
from runtime.openai_provider import OpenAIProvider
from runtime.tool_adapter import ToolAdapter
from tools.registry import Tool, ToolRegistry

load_dotenv()


def build_app():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Copy .env.example to .env and add your API key.")
    if not os.getenv("SAIT_MODEL"):
        raise RuntimeError("SAIT_MODEL is missing. Set it to an API model available in your account.")

    workspace = Path(os.getenv("SAIT_WORKSPACE", "workspace")).resolve()
    coding = CodingEngine(str(workspace))
    browser = BrowserController(BrowserConfig(headless=False)).start()
    registry = ToolRegistry()

    registry.register(Tool(
        name="read_file",
        description="Read a UTF-8 text file inside the coding workspace.",
        handler=coding.read_file,
        parameters={"type": "object", "properties": {"relative_path": {"type": "string"}}, "required": ["relative_path"], "additionalProperties": False},
    ))
    registry.register(Tool(
        name="write_file",
        description="Create or replace a UTF-8 text file inside the coding workspace.",
        handler=coding.write_file,
        parameters={"type": "object", "properties": {"relative_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["relative_path", "content"], "additionalProperties": False},
    ))
    registry.register(Tool(
        name="list_files",
        description="List files inside the coding workspace.",
        handler=coding.list_files,
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
    ))
    registry.register(Tool(
        name="browser_open",
        description="Open a URL in the local Chromium browser and return its title and final URL.",
        handler=browser.open,
        parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"], "additionalProperties": False},
    ))
    registry.register(Tool(
        name="browser_text",
        description="Read visible text from the current browser page using a CSS selector.",
        handler=browser.text,
        parameters={"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"], "additionalProperties": False},
    ))
    registry.register(Tool(
        name="browser_click",
        description="Click an element on the current browser page using a CSS selector.",
        handler=browser.click,
        parameters={"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"], "additionalProperties": False},
    ))
    registry.register(Tool(
        name="browser_fill",
        description="Fill an input or textarea on the current browser page using a CSS selector.",
        handler=browser.fill,
        parameters={"type": "object", "properties": {"selector": {"type": "string"}, "value": {"type": "string"}}, "required": ["selector", "value"], "additionalProperties": False},
    ))
    registry.register(Tool(
        name="browser_screenshot",
        description="Take a full-page screenshot of the current browser page and save it to the workspace.",
        handler=lambda path="browser_screenshots/latest.png": browser.screenshot(str(workspace / path)),
        parameters={"type": "object", "properties": {"path": {"type": "string"}}, "additionalProperties": False},
    ))

    runtime = AIRuntime(OpenAIProvider())
    orchestrator = Orchestrator(runtime, ToolAdapter(registry))
    return orchestrator, TaskMemory()


def main():
    orchestrator, memory = build_app()
    print("TOP SECRET AI - local runtime")
    print("Browser: Chromium connected")
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
