from typing import Any
import json
import os


class OpenAIProvider:
    """OpenAI-compatible Responses API adapter with function calling.

    Supports OpenAI directly and OpenRouter through OPENAI_BASE_URL.
    Tool-call output items are returned so the orchestrator can preserve
    the full conversation when a provider does not support response chaining.
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

        # Do not use previous_response_id for OpenRouter. The orchestrator
        # supplies the accumulated conversation instead.
        if previous_response_id and not self.is_openrouter:
            kwargs["previous_response_id"] = previous_response_id

        response = self.client.responses.create(**kwargs)
        calls = []
        text_parts = []
        output_items = []

        for item in response.output:
            item_type = getattr(item, "type", None)

            if item_type == "function_call":
                arguments = json.loads(item.arguments)
                calls.append({
                    "name": item.name,
                    "call_id": item.call_id,
                    "arguments": arguments,
                })
                output_items.append({
                    "type": "function_call",
                    "name": item.name,
                    "call_id": item.call_id,
                    "arguments": item.arguments,
                })

            elif item_type == "message":
                content_items = []
                for content in getattr(item, "content", []) or []:
                    text = getattr(content, "text", None)
                    if text:
                        text_parts.append(text)
                    content_type = getattr(content, "type", "output_text")
                    if text:
                        content_items.append({"type": content_type, "text": text})

                if content_items:
                    output_items.append({
                        "type": "message",
                        "role": "assistant",
                        "content": content_items,
                    })

        return {
            "text": "\n".join(text_parts),
            "function_calls": calls,
            "output_items": output_items,
            "response_id": response.id,
        }
