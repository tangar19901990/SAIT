# TOP SECRET AI Agent

Universal local AI agent for Windows 10.

## Vision

A personal agent that can reason, plan, use a browser, work with files, write and test code, use GitHub, create modern interfaces, and later run autonomous scheduled tasks.

## Architecture

- `agent/` orchestration and planning
- `tools/` safe tool interfaces
- `browser/` browser automation adapter
- `coding/` coding workspace and execution
- `memory/` persistent project memory
- `security/` permissions and approval gates
- `interface/` local control panel
- `tests/` automated tests
- `projects/` isolated workspaces for generated projects

## Development strategy

Phase 1 is a local Windows-first MVP. The agent must be able to receive a natural-language task, make a plan, use tools, inspect results, recover from errors, and return a clear report.

Dangerous operations require explicit approval. API keys and secrets must never be committed to GitHub.

## Status

Scaffold initialized. Next milestone: local runtime + provider adapter + tool registry + browser control + coding workspace.
