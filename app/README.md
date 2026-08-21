# Local launcher

Run from the repository root with Python 3.11+:

```bash
python -m app.main
```

This first launcher is intentionally a smoke-test shell. It uses a placeholder
provider until a real AI provider adapter is configured. Do not put API keys in
source control; use environment variables or a local `.env` ignored by Git.
