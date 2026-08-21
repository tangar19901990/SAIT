# TOP SECRET AI Agent

Universal local AI agent for Windows 10/11.

## Current MVP

SAIT can:

- switch between Gemini, Claude, OpenAI, Groq and OpenRouter;
- run in automatic provider-fallback mode;
- control a visible Chromium browser with Playwright;
- open pages, read text/HTML, click, fill forms, press keys and take screenshots;
- read, write and list files inside its coding workspace;
- keep a local JSONL task history;
- verify web-research results instead of treating search snippets as facts;
- stop repeated tool loops and bound oversized tool output.

## Project structure

- `app/` application entry point and CLI
- `runtime/` provider adapters and runtime facade
- `orchestrator/` planning, tool execution and loop guards
- `browser/` Playwright browser controller
- `coding/` workspace file operations
- `memory/` local task history
- `tools/` tool registry and adapter
- `agent/`, `core/`, `design/` experimental modules for later expansion

## Windows launch

1. Copy `.env.example` to `.env`.
2. Add at least one provider API key.
3. Run `run_sait.bat`.
4. At `YOU >`, use `/help` for provider commands.

API keys belong only in the local `.env`. Never commit real secrets to GitHub.
