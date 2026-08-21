from typing import Any
import json
import os


class OpenAIProvider:
    """OpenAI-compatible Responses API adapter with function calling.

    Supports OpenAI directly and OpenRouter through OPENAI_BASE_URL.
    OpenRouter does not support Responses API conversation chaining via
    previous_response_id, so that parameter is intentionally omitted there.
    """

    def __init__(self, model: str | None = None):
        from openai import OpenAI

        self.base_url = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
        self.is_openrouter = "openrouter.ai" in self.base_url.lower()
        self.client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=self.base_url or None,
        )
        self.model = model or os.getenv("SAIT_MODEL", "gpt-5.6")

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        previous_response_id: str | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "input": messages,
            "tools": tools or [],
        }

        # OpenAI supports conversation chaining with previous_response_id.
        # OpenRouter currently rejects this field in its Responses API.
        if previous_response_id and not self.is_openrouter:
            kwargs["previous_response_id"] = previous_response_id

        response = self.client.responses.create(**kwargs)
        calls = []
        text_parts = []
        for item in response.output:
            item_type = getattr(item, "type", None)
            if item_type == "function_call":
                calls.append({
                    "name": item.name,
                    "call_id": item.call_id,
                    "arguments": json.loads(item.arguments),
                })
            elif item_type == "message":
                for content in getattr(item, "content", []) or []:
                    text = getattr(content, "text", None)
                    if text:
                        text_parts.append(text)
        return {
            "text": "\n".join(text_parts),
            "function_calls": calls,
            "response_id": response.id,
        }
