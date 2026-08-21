import os
from pathlib import Path

from dotenv import load_dotenv
from browser import BrowserController, BrowserConfig
from coding import CodingEngine
from memory import TaskMemory
from orchestrator import Orchestrator
from runtime import AIRuntime
from runtime.multi_provider import MultiProvider
from runtime.tool_adapter import ToolAdapter
from tools.registry import Tool, ToolRegistry

load_dotenv()


def build_app():
    if not any(os.getenv(k) for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY")):
        raise RuntimeError("No AI provider key configured. Add at least one provider key to .env")
    workspace = Path(os.getenv("SAIT_WORKSPACE", "workspace")).resolve()
    coding = CodingEngine(str(workspace))
    browser = BrowserController(BrowserConfig(headless=False)).start()
    registry = ToolRegistry()

    def add(name, description, handler, properties, required):
        registry.register(Tool(name=name, description=description, handler=handler, parameters={"type": "object", "properties": properties, "required": required, "additionalProperties": False}))

    add("read_file", "Read a UTF-8 text file inside the coding workspace.", coding.read_file, {"relative_path": {"type": "string"}}, ["relative_path"])
    add("write_file", "Create or replace a UTF-8 text file inside the coding workspace.", coding.write_file, {"relative_path": {"type": "string"}, "content": {"type": "string"}}, ["relative_path", "content"])
    add("list_files", "List files inside the coding workspace.", coding.list_files, {}, [])
    add("browser_open", "Open a URL in local Chromium and return title and final URL.", browser.open, {"url": {"type": "string"}}, ["url"])
    add("browser_current", "Return current browser URL and page title.", browser.current, {}, [])
    add("browser_text", "Read visible text from the current page using a CSS selector.", browser.text, {"selector": {"type": "string"}}, ["selector"])
    add("browser_html", "Read outer HTML of an element using a CSS selector.", browser.html, {"selector": {"type": "string"}}, ["selector"])
    add("browser_click", "Click an element using a CSS selector.", browser.click, {"selector": {"type": "string"}}, ["selector"])
    add("browser_fill", "Fill an input using a CSS selector.", browser.fill, {"selector": {"type": "string"}, "value": {"type": "string"}}, ["selector", "value"])
    add("browser_press", "Press a keyboard key on an element.", browser.press, {"selector": {"type": "string"}, "key": {"type": "string"}}, ["selector", "key"])
    add("browser_screenshot", "Save a full-page screenshot to the coding workspace.", lambda path: browser.screenshot(str(workspace / path)), {"path": {"type": "string"}}, ["path"])

    provider = MultiProvider()
    return Orchestrator(AIRuntime(provider), ToolAdapter(registry)), TaskMemory(), provider


def main():
    orchestrator, memory, provider = build_app()
    print("TOP SECRET AI v3.0 - MULTI AI POOL")
    print("Browser: Chromium connected")
    print("Providers: " + ", ".join(provider.providers))
    print("Type 'exit' to quit.")
    while True:
        try:
            goal = input("\nYOU > ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if goal.lower() in {"exit", "quit"}: break
        if not goal: continue
        try:
            state = orchestrator.run(goal)
            summary = state.history[-1].get("output", state.status) if state.history else state.status
            memory.remember(goal, state.status, str(summary))
            print(f"AI [{provider.last_provider}] > {summary}")
        except Exception as exc:
            print(f"ERROR > {exc}")


if __name__ == "__main__":
    main()
