import os
from typing import Any

from openai import OpenAI


class OpenAIProvider:
    """OpenAI Responses API adapter for SAIT."""

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("SAIT_MODEL", "gpt-5.6")
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def complete(self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            input=messages,
        )
        return {
            "action": "finish",
            "output": response.output_text,
            "raw": response,
        }
