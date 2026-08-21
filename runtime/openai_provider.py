from typing import Any
import json
import os
import time


class OpenAIProvider:
    """OpenAI-compatible Responses API adapter with function calling.

    Supports OpenAI directly and OpenRouter through OPENAI_BASE_URL.
    OpenRouter can use a comma-separated SAIT_FALLBACK_MODELS list. The
    provider automatically tries the next model for transient/provider/model
    errors. An account-wide OpenRouter free-tier quota cannot be bypassed by
    switching models, so daily free-quota exhaustion is reported clearly.
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

        configured = os.getenv("SAIT_FALLBACK_MODELS", "")
        self.fallback_models = [m.strip() for m in configured.split(",") if m.strip()]
        self.models = []
        for candidate in [self.model, *self.fallback_models]:
            if candidate and candidate not in self.models:
                self.models.append(candidate)

    def _is_free_daily_quota_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return (
            "free-models-per-day" in text
            or "openrouter_free_tier_daily" in text
            or "add 10 credits to unlock 1000 free model requests per day" in text
        )

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        previous_response_id: str | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None

        for index, model in enumerate(self.models):
            kwargs: dict[str, Any] = {
                "model": model,
                "input": messages,
                "tools": tools or [],
            }

            # Do not use previous_response_id for OpenRouter. The orchestrator
            # supplies the accumulated conversation instead.
            if previous_response_id and not self.is_openrouter:
                kwargs["previous_response_id"] = previous_response_id

            try:
                response = self.client.responses.create(**kwargs)
            except Exception as exc:
                last_error = exc

                # The OpenRouter free daily quota is account-wide. Trying
                # another free model cannot increase the remaining quota.
                if self.is_openrouter and self._is_free_daily_quota_error(exc):
                    raise RuntimeError(
                        "OpenRouter free-model daily quota is exhausted. "
                        "Switching free models cannot bypass this account-wide limit. "
                        "Wait for the reset or add OpenRouter credits."
                    ) from exc

                # For other transient/provider/model errors, try the next
                # configured model before giving up.
                if index + 1 < len(self.models):
                    time.sleep(0.5)
                    continue
                raise

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
                "model": model,
            }

        if last_error:
            raise last_error
        raise RuntimeError("No SAIT model is configured.")
