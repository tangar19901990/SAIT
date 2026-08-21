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

    def add(name, description, handler, properties, required):
        registry.register(Tool(
            name=name,
            description=description,
            handler=handler,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        ))

    add("read_file", "Read a UTF-8 text file inside the coding workspace.", coding.read_file,
        {"relative_path": {"type": "string"}}, ["relative_path"])
    add("write_file", "Create or replace a UTF-8 text file inside the coding workspace.", coding.write_file,
        {"relative_path": {"type": "string"}, "content": {"type": "string"}}, ["relative_path", "content"])
    add("list_files", "List files inside the coding workspace.", coding.list_files, {}, [])

    add("browser_open", "Open a URL in local Chromium and return its title and final URL.", browser.open,
        {"url": {"type": "string"}}, ["url"])
    add("browser_current", "Return the current browser URL and page title.", browser.current, {}, [])
    add("browser_text", "Read visible text from the current browser page using a CSS selector.", browser.text,
        {"selector": {"type": "string"}}, ["selector"])
    add("browser_html", "Read the outer HTML of an element on the current browser page.", browser.html,
        {"selector": {"type": "string"}}, ["selector"])
    add("browser_click", "Click an element on the current browser page using a CSS selector.", browser.click,
        {"selector": {"type": "string"}}, ["selector"])
    add("browser_fill", "Fill an input or textarea using a CSS selector.", browser.fill,
        {"selector": {"type": "string"}, "value": {"type": "string"}}, ["selector", "value"])
    add("browser_press", "Press a keyboard key on an element using a CSS selector.", browser.press,
        {"selector": {"type": "string"}, "key": {"type": "string"}}, ["selector", "key"])
    add("browser_screenshot", "Take a full-page screenshot and save it to the coding workspace.",
        lambda path: browser.screenshot(str(workspace / path)),
        {"path": {"type": "string"}}, ["path"])

    runtime = AIRuntime(OpenAIProvider())
    orchestrator = Orchestrator(runtime, ToolAdapter(registry))
    return orchestrator, TaskMemory()


def main():
    orchestrator, memory = build_app()
    print("TOP SECRET AI v2.0 - local runtime")
    print("Browser: Chromium connected")
    print("Coding workspace: ready")
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
        try:
            state = orchestrator.run(goal)
            summary = state.history[-1].get("output", state.status) if state.history else state.status
            memory.remember(goal, state.status, str(summary))
            print(f"AI  > {summary}")
        except Exception as exc:
            print(f"ERROR > {exc}")


if __name__ == "__main__":
    main()
