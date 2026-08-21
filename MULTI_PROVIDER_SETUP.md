# SAIT Multi-Provider setup

SAIT can try multiple providers in the order in `SAIT_PROVIDERS`.

Example `.env`:

```env
SAIT_PROVIDERS=openai,gemini,groq,anthropic,openrouter
SAIT_WORKSPACE=workspace

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-luna

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b

ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-5

OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
```

Only providers with a key are used. If the first configured provider fails, SAIT tries the next configured provider.

Important: Claude's API is not a generally unlimited free API. Gemini and Groq publish free-tier limits. OpenRouter free models also have daily limits. OpenAI's complimentary data-sharing tokens are only available to eligible organizations and require a positive account balance.

Do not commit the real `.env` file or API keys.
