from __future__ import annotations

import json
import os
from typing import Any

import httpx

from runtime.multi_provider import MultiProvider


class AnthropicSafeProvider(MultiProvider):
    """Anthropic adapter with strict tool/message formatting."""

    @staticmethod
    def _schema(parameters: Any) -> dict[str, Any]:
        schema = dict(parameters or {"type": "object", "properties": {}})
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        # Keep only portable JSON Schema fields used by Anthropic tools.
        schema.pop("additionalProperties", None)
        return schema

    def _anthropic(self, messages, tools):
        system = ""
        converted: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role")
            if role == "system":
                system = str(msg.get("content", ""))
                continue

            if role in {"user", "assistant"}:
                converted.append({"role": role, "content": msg.get("content", "")})
                continue

            if msg.get("type") == "function_call":
                try:
                    args = json.loads(msg.get("arguments", "{}"))
                except (TypeError, json.JSONDecodeError):
                    args = {}
                converted.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": msg.get("call_id"),
                        "name": msg.get("name", ""),
                        "input": args,
                    }],
                })
                continue

            if msg.get("type") == "function_call_output":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("call_id"),
                        "content": str(msg.get("output", "")),
                    }],
                })

        model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
        tool_payload = [
            {
                "name": t["name"],
                "description": t.get("description", "")[:4000],
                "input_schema": self._schema(t.get("parameters")),
            }
            for t in (tools or [])
        ]

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 8192,
            "messages": converted,
        }
        if system:
            payload["system"] = system
        if tool_payload:
            payload["tools"] = tool_payload

        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=120,
        )

        if response.status_code >= 400:
            try:
                error = response.json().get("error", {})
                detail = error.get("message") or response.text
            except Exception:
                detail = response.text
            raise RuntimeError(f"Anthropic API {response.status_code}: {detail[:1000]}")

        data = response.json()
        calls: list[dict[str, Any]] = []
        texts: list[str] = []
        assistant_blocks: list[dict[str, Any]] = []

        for item in data.get("content", []):
            item_type = item.get("type")
            if item_type == "text":
                text = item.get("text", "")
                texts.append(text)
                assistant_blocks.append({"type": "text", "text": text})
            elif item_type == "tool_use":
                call_id = item.get("id")
                name = item.get("name", "")
                args = item.get("input") or {}
                calls.append({
                    "name": name,
                    "call_id": call_id,
                    "arguments": args,
                })
                # Keep tool_use and text blocks in ONE assistant message.
                # Anthropic rejects consecutive assistant messages here.
                assistant_blocks.append({
                    "type": "tool_use",
                    "id": call_id,
                    "name": name,
                    "input": args,
                })

        output_items: list[dict[str, Any]] = []
        if assistant_blocks:
            output_items.append({
                "type": "message",
                "role": "assistant",
                "content": assistant_blocks,
            })

        return {
            "text": "\n".join(texts),
            "function_calls": calls,
            "output_items": output_items,
            "response_id": None,
            "model": model,
            "provider": "anthropic",
        }
