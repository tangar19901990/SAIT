from typing import Any
import json
import os


class OpenAIProvider:
    """OpenAI Responses API adapter with function calling."""

    def __init__(self, model: str | None = None):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
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
        if previous_response_id:
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
