from __future__ import annotations

import json
import os
from typing import Any

import httpx


class MultiProvider:
    """Provider pool for OpenAI, Gemini, Groq, Anthropic and OpenRouter.

    Providers are tried in SAIT_PROVIDERS order. A provider is skipped when
    its API key is missing. Tool calls are normalized to the format expected
    by the existing orchestrator.
    """

    def __init__(self) -> None:
        self.providers = [
            p.strip().lower()
            for p in os.getenv("SAIT_PROVIDERS", "openai,gemini,groq,anthropic,openrouter").split(",")
            if p.strip()
        ]
        self.is_openrouter = False
        self.last_provider = ""

    def _configured(self, provider: str) -> bool:
        keys = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        return bool(os.getenv(keys.get(provider, "")))

    @staticmethod
    def _chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            if role in {"system", "user"}:
                out.append({"role": role, "content": msg.get("content", "")})
                continue
            if role == "assistant":
                content = msg.get("content", "")
                item = {"role": "assistant", "content": content}
                if msg.get("tool_calls"):
                    item["tool_calls"] = msg["tool_calls"]
                out.append(item)
                continue
            if msg.get("type") == "function_call":
                out.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": msg.get("call_id"),
                        "type": "function",
                        "function": {
                            "name": msg.get("name"),
                            "arguments": msg.get("arguments", "{}"),
                        },
                    }],
                })
                continue
            if msg.get("type") == "function_call_output":
                out.append({
                    "role": "tool",
                    "tool_call_id": msg.get("call_id"),
                    "content": msg.get("output", ""),
                })
        return out

    @staticmethod
    def _chat_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        result = []
        for tool in tools or []:
            result.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                },
            })
        return result

    @staticmethod
    def _normalize_chat_response(data: dict[str, Any], provider: str, model: str) -> dict[str, Any]:
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        text = message.get("content") or ""
        calls = []
        output_items = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            call_id = tc.get("id") or f"{provider}-call"
            name = fn.get("name", "")
            calls.append({"name": name, "call_id": call_id, "arguments": args})
            output_items.append({
                "type": "function_call",
                "name": name,
                "call_id": call_id,
                "arguments": raw_args,
            })
        if text:
            output_items.append({
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            })
        return {
            "text": text,
            "function_calls": calls,
            "output_items": output_items,
            "response_id": data.get("id"),
            "model": model,
            "provider": provider,
        }

    def _openai(self, messages, tools, previous_response_id):
        from runtime.openai_provider import OpenAIProvider
        return OpenAIProvider().complete(messages, tools=tools, previous_response_id=previous_response_id)

    def _compatible(self, provider: str, messages, tools):
        configs = {
            "gemini": (
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                os.getenv("GEMINI_API_KEY"),
                os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            ),
            "groq": (
                "https://api.groq.com/openai/v1/chat/completions",
                os.getenv("GROQ_API_KEY"),
                os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            ),
            "openrouter": (
                "https://openrouter.ai/api/v1/chat/completions",
                os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"),
                os.getenv("OPENROUTER_MODEL", "openrouter/free"),
            ),
        }
        url, key, model = configs[provider]
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": self._chat_messages(messages),
            "tools": self._chat_tools(tools),
            "temperature": 0.2,
        }
        response = httpx.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return self._normalize_chat_response(response.json(), provider, model)

    def _anthropic(self, messages, tools):
        system = ""
        converted = []
        for msg in messages:
            if msg.get("role") == "system":
                system = str(msg.get("content", ""))
            elif msg.get("role") in {"user", "assistant"}:
                converted.append({"role": msg["role"], "content": msg.get("content", "")})
            elif msg.get("type") == "function_call_output":
                converted.append({"role": "user", "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("call_id"),
                    "content": msg.get("output", ""),
                }]})
            elif msg.get("type") == "function_call":
                converted.append({"role": "assistant", "content": [{
                    "type": "tool_use",
                    "id": msg.get("call_id"),
                    "name": msg.get("name"),
                    "input": json.loads(msg.get("arguments", "{}")),
                }]})
        anthropic_tools = []
        for tool in tools or []:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", {"type": "object", "properties": {}}),
            })
        headers = {
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
        payload = {
            "model": model,
            "max_tokens": 8192,
            "system": system,
            "messages": converted,
            "tools": anthropic_tools,
        }
        response = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        calls = []
        output_items = []
        text_parts = []
        for item in data.get("content", []):
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif item.get("type") == "tool_use":
                call_id = item.get("id")
                calls.append({"name": item.get("name"), "call_id": call_id, "arguments": item.get("input", {})})
                output_items.append({
                    "type": "function_call",
                    "name": item.get("name"),
                    "call_id": call_id,
                    "arguments": json.dumps(item.get("input", {})),
                })
        text = "\n".join(text_parts)
        if text:
            output_items.append({"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]})
        return {"text": text, "function_calls": calls, "output_items": output_items, "response_id": data.get("id"), "model": model, "provider": "anthropic"}

    def complete(self, messages, tools=None, previous_response_id=None):
        errors = []
        for provider in self.providers:
            if not self._configured(provider):
                continue
            try:
                if provider == "openai":
                    result = self._openai(messages, tools, previous_response_id)
                elif provider == "anthropic":
                    result = self._anthropic(messages, tools)
                else:
                    result = self._compatible(provider, messages, tools)
                self.last_provider = provider
                self.is_openrouter = provider == "openrouter"
                return result
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                continue
        raise RuntimeError("All configured AI providers failed:\n" + "\n".join(errors))
