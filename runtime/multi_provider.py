from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx


class MultiProvider:
    """Provider pool for OpenAI, Gemini, Groq, Anthropic and OpenRouter."""

    def __init__(self) -> None:
        self.providers = [p.strip().lower() for p in os.getenv("SAIT_PROVIDERS", "openai,gemini,groq,anthropic,openrouter").split(",") if p.strip()]
        self.is_openrouter = False
        self.last_provider = ""

    def _configured(self, provider: str) -> bool:
        return bool(os.getenv({
            "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY", "openrouter": "OPENROUTER_API_KEY",
        }.get(provider, "")))

    @staticmethod
    def _chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for msg in messages:
            role = msg.get("role")
            if role in {"system", "user"}:
                out.append({"role": role, "content": msg.get("content", "")})
            elif role == "assistant":
                item = {"role": "assistant", "content": msg.get("content", "")}
                if msg.get("tool_calls"): item["tool_calls"] = msg["tool_calls"]
                out.append(item)
            elif msg.get("type") == "function_call":
                out.append({"role": "assistant", "content": None, "tool_calls": [{"id": msg.get("call_id"), "type": "function", "function": {"name": msg.get("name"), "arguments": msg.get("arguments", "{}")}}]})
            elif msg.get("type") == "function_call_output":
                out.append({"role": "tool", "tool_call_id": msg.get("call_id"), "content": msg.get("output", "")})
        return out

    @staticmethod
    def _chat_tools(tools):
        return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters", {"type": "object", "properties": {}})}} for t in (tools or [])]

    @staticmethod
    def _normalize_chat_response(data, provider, model):
        message = ((data.get("choices") or [{}])[0].get("message") or {})
        text = message.get("content") or ""
        calls, output_items = [], []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            raw_args = fn.get("arguments") or "{}"
            try: args = json.loads(raw_args)
            except json.JSONDecodeError: args = {}
            call_id = tc.get("id") or f"{provider}-call"
            calls.append({"name": fn.get("name", ""), "call_id": call_id, "arguments": args})
            output_items.append({"type": "function_call", "name": fn.get("name", ""), "call_id": call_id, "arguments": raw_args})
        if text:
            output_items.append({"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]})
        return {"text": text, "function_calls": calls, "output_items": output_items, "response_id": data.get("id"), "model": model, "provider": provider}

    def _openai(self, messages, tools, previous_response_id):
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        kwargs = {"model": model, "input": messages, "tools": tools or []}
        if previous_response_id: kwargs["previous_response_id"] = previous_response_id
        response = client.responses.create(**kwargs)
        calls, texts, output_items = [], [], []
        for item in response.output:
            if getattr(item, "type", None) == "function_call":
                calls.append({"name": item.name, "call_id": item.call_id, "arguments": json.loads(item.arguments)})
                output_items.append({"type": "function_call", "name": item.name, "call_id": item.call_id, "arguments": item.arguments})
            elif getattr(item, "type", None) == "message":
                content_items = []
                for content in getattr(item, "content", []) or []:
                    text = getattr(content, "text", None)
                    if text:
                        texts.append(text); content_items.append({"type": getattr(content, "type", "output_text"), "text": text})
                if content_items: output_items.append({"type": "message", "role": "assistant", "content": content_items})
        return {"text": "\n".join(texts), "function_calls": calls, "output_items": output_items, "response_id": response.id, "model": model, "provider": "openai"}

    def _discover_gemini_model(self, api_key: str) -> str:
        """Discover a model available to this API key that supports generateContent."""
        configured = os.getenv("GEMINI_MODEL", "").strip()
        response = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key, "pageSize": 100},
            timeout=30,
        )
        response.raise_for_status()
        models = response.json().get("models", [])
        candidates = []
        for item in models:
            methods = item.get("supportedGenerationMethods") or []
            name = str(item.get("name", ""))
            if "generateContent" not in methods or not name:
                continue
            short = name.split("/", 1)[-1]
            if configured and short == configured:
                return short
            lower = short.lower()
            score = 0
            if "flash" in lower: score += 100
            if "pro" in lower: score += 50
            if "latest" in lower: score += 10
            if "exp" in lower or "preview" in lower: score -= 5
            candidates.append((score, short))
        if not candidates:
            raise RuntimeError("Gemini API key has no model available with generateContent.")
        candidates.sort(reverse=True)
        return candidates[0][1]

    def _gemini(self, messages, tools):
        """Use Google's native Gemini generateContent API with automatic model discovery."""
        api_key = os.environ["GEMINI_API_KEY"]
        model = self._discover_gemini_model(api_key)
        system_parts, contents = [], []
        for msg in messages:
            role = msg.get("role")
            text = str(msg.get("content", ""))
            if role == "system":
                system_parts.append(text)
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": text}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": text}]})
            elif msg.get("type") == "function_call_output":
                contents.append({"role": "user", "parts": [{"functionResponse": {"name": msg.get("name", "tool"), "response": {"result": msg.get("output", "")}}}]})

        body: dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": 0.2}}
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
        if tools:
            declarations = []
            for t in tools:
                schema = dict(t.get("parameters") or {"type": "object", "properties": {}})
                schema.pop("additionalProperties", None)
                declarations.append({"name": t["name"], "description": t.get("description", ""), "parameters": schema})
            body["tools"] = [{"functionDeclarations": declarations}]

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        response = httpx.post(url, params={"key": api_key}, json=body, timeout=120)
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates") or []
        parts = ((candidates[0].get("content") or {}).get("parts") if candidates else []) or []
        texts, calls, output_items = [], [], []
        for part in parts:
            if part.get("text"):
                texts.append(part["text"])
            fc = part.get("functionCall")
            if fc:
                call_id = f"gemini-{len(calls)+1}"
                args = fc.get("args") or {}
                calls.append({"name": fc.get("name", ""), "call_id": call_id, "arguments": args})
                output_items.append({"type": "function_call", "name": fc.get("name", ""), "call_id": call_id, "arguments": json.dumps(args)})
        text = "\n".join(texts)
        if text:
            output_items.append({"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]})
        return {"text": text, "function_calls": calls, "output_items": output_items, "response_id": None, "model": model, "provider": "gemini"}

    def _compatible(self, provider, messages, tools):
        configs = {
            "groq": ("https://api.groq.com/openai/v1/chat/completions", os.getenv("GROQ_API_KEY"), os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")),
            "openrouter": ("https://openrouter.ai/api/v1/chat/completions", os.getenv("OPENROUTER_API_KEY"), os.getenv("OPENROUTER_MODEL", "openrouter/free")),
        }
        url, key, model = configs[provider]
        response = httpx.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json={"model": model, "messages": self._chat_messages(messages), "tools": self._chat_tools(tools), "temperature": 0.2}, timeout=120)
        response.raise_for_status()
        return self._normalize_chat_response(response.json(), provider, model)

    def _anthropic(self, messages, tools):
        system, converted = "", []
        for msg in messages:
            if msg.get("role") == "system": system = str(msg.get("content", ""))
            elif msg.get("role") in {"user", "assistant"}: converted.append({"role": msg["role"], "content": msg.get("content", "")})
            elif msg.get("type") == "function_call_output": converted.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": msg.get("call_id"), "content": msg.get("output", "")} ]})
        model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
        tools_payload = [{"name": t["name"], "description": t.get("description", ""), "input_schema": t.get("parameters", {"type": "object", "properties": {}})} for t in (tools or [])]
        response = httpx.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"}, json={"model": model, "max_tokens": 8192, "system": system, "messages": converted, "tools": tools_payload}, timeout=120)
        response.raise_for_status()
        data = response.json(); calls, output_items, texts = [], [], []
        for item in data.get("content", []):
            if item.get("type") == "text": texts.append(item.get("text", ""))
            elif item.get("type") == "tool_use":
                call_id = item.get("id"); calls.append({"name": item.get("name"), "call_id": call_id, "arguments": item.get("input", {})}); output_items.append({"type": "function_call", "name": item.get("name"), "call_id": call_id, "arguments": json.dumps(item.get("input", {}))})
        text = "\n".join(texts)
        if text: output_items.append({"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]})
        return {"text": text, "function_calls": calls, "output_items": output_items, "response_id": data.get("id"), "model": model, "provider": "anthropic"}

    def complete(self, messages, tools=None, previous_response_id=None):
        errors = []
        for provider in self.providers:
            if not self._configured(provider): continue
            try:
                if provider == "openai": result = self._openai(messages, tools, previous_response_id)
                elif provider == "gemini": result = self._gemini(messages, tools)
                elif provider == "anthropic": result = self._anthropic(messages, tools)
                else: result = self._compatible(provider, messages, tools)
                self.last_provider = provider; self.is_openrouter = provider == "openrouter"; return result
            except Exception as exc:
                errors.append(f"{provider}: {exc}"); time.sleep(0.2)
        raise RuntimeError("All configured AI providers failed:\n" + "\n".join(errors))
