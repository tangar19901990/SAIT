import os
from pathlib import Path

from dotenv import load_dotenv

from browser import BrowserController, BrowserConfig
from coding import CodingEngine
from memory import TaskMemory
from orchestrator import Orchestrator
from runtime import AIRuntime
from runtime.anthropic_provider_patch import AnthropicSafeProvider
from runtime.tool_adapter import ToolAdapter
from tools.registry import Tool, ToolRegistry

load_dotenv()

PROVIDER_KEYS = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
)


def build_app():
    if not any(os.getenv(k) for k in PROVIDER_KEYS):
        raise RuntimeError("No AI API key is configured. Add at least one key to .env")

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

    def safe_screenshot(relative_path: str):
        target = (workspace / relative_path).resolve()
        if workspace != target and workspace not in target.parents:
            raise ValueError("Screenshot path escapes the coding workspace")
        return browser.screenshot(str(target))

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
    add("browser_screenshot", "Take a full-page screenshot and save it to the coding workspace.", safe_screenshot,
        {"path": {"type": "string"}}, ["path"])

    provider = AnthropicSafeProvider()
    runtime = AIRuntime(provider)
    orchestrator = Orchestrator(runtime, ToolAdapter(registry))
    orchestrator.browser = browser
    return orchestrator, TaskMemory(), provider


def print_help(provider):
    print("\nКоманди провайдера:")
    print("  /auto         автоматичний режим")
    print("  /gemini       тільки Gemini")
    print("  /claude       тільки Claude")
    print("  /gpt          тільки OpenAI")
    print("  /groq         тільки Groq")
    print("  /openrouter   тільки OpenRouter")
    print("  /provider     показати поточний режим")
    print("  /providers    показати доступні ключі")
    print("  /help         показати допомогу")
    print(f"\nПоточний режим: {provider.get_provider()}")


def main():
    orchestrator, memory, provider = build_app()
    print("TOP SECRET AI v3.1 - local runtime")
    print("Browser: Chromium connected")
    print("Coding workspace: ready")
    print("AI providers: ready")
    print("Type /help for provider commands, or 'exit' to quit.")

    command_map = {
        "/auto": "auto",
        "/gemini": "gemini",
        "/claude": "anthropic",
        "/gpt": "openai",
        "/groq": "groq",
        "/openrouter": "openrouter",
    }

    try:
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

            command = goal.lower()
            if command in command_map:
                selected = command_map[command]
                provider.set_provider(selected)
                print(f"AI MODE > {selected}")
                continue
            if command == "/provider":
                print(f"AI MODE > {provider.get_provider()}")
                print(f"LAST AI > {provider.last_provider or 'none'}")
                continue
            if command == "/providers":
                available = provider.available_providers()
                print("AVAILABLE > " + (", ".join(available) if available else "none"))
                continue
            if command == "/help":
                print_help(provider)
                continue

            try:
                state = orchestrator.run(goal)
                summary = state.history[-1].get("output", state.status) if state.history else state.status
                memory.remember(goal, state.status, str(summary))
                used = provider.last_provider or provider.get_provider()
                print(f"AI [{used}] > {summary}")
            except Exception as exc:
                print(f"ERROR > {exc}")
    finally:
        orchestrator.browser.stop()


if __name__ == "__main__":
    main()
