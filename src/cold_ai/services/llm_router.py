from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import settings
from .ai_agent_runtime import AgentLLMConfig


class LLMRouter:
    def _requires_api_key(self, provider: str) -> bool:
        return provider not in {"ollama", "vllm"}

    def available(self, runtime_config: AgentLLMConfig | None = None) -> bool:
        config = runtime_config
        provider = config.provider if config else "openai"
        api_key = config.api_key if config else settings.llm_api_key
        models = config.models if config else settings.llm_models
        if not models:
            return False
        if self._requires_api_key(provider):
            return bool(api_key)
        return True

    def rewrite_email(
        self,
        payload: dict,
        runtime_config: AgentLLMConfig | None = None,
        custom_prompt: str | None = None,
    ) -> dict | None:
        if not self.available(runtime_config):
            return None

        system_prompt = custom_prompt or (
            "You are a sales outreach rewriting assistant. "
            "Rewrite for a human, concise, credible tone. Avoid hype, spammy phrasing, and robotic language. "
            "Return strict JSON with keys: subject, body, confidence. "
            "confidence is a float between 0 and 1."
        )
        return self.run_json_task(
            system_prompt=system_prompt,
            payload=payload,
            runtime_config=runtime_config,
            temperature=0.6,
        )

    def test_connection(self, runtime_config: AgentLLMConfig) -> dict:
        if not runtime_config.models:
            return {
                "ok": False,
                "provider": runtime_config.provider,
                "model": None,
                "error": "No models configured",
            }

        if self._requires_api_key(runtime_config.provider) and not runtime_config.api_key:
            return {
                "ok": False,
                "provider": runtime_config.provider,
                "model": runtime_config.models[0],
                "error": "API key is required for this provider",
            }

        probe = self.run_json_task(
            system_prompt=(
                "You are a connectivity probe. Return strict JSON with one key: ok (boolean true)."
            ),
            payload={"ping": "cold-ai"},
            runtime_config=runtime_config,
            temperature=0,
        )

        if probe and isinstance(probe, dict):
            return {
                "ok": True,
                "provider": runtime_config.provider,
                "model": runtime_config.models[0],
                "base_url": runtime_config.base_url,
            }

        return {
            "ok": False,
            "provider": runtime_config.provider,
            "model": runtime_config.models[0],
            "base_url": runtime_config.base_url,
            "error": "Connection failed. Verify API key, base URL, and model name.",
        }

    def run_json_task(
        self,
        system_prompt: str,
        payload: dict,
        runtime_config: AgentLLMConfig | None = None,
        temperature: float = 0.2,
    ) -> dict | None:
        config = runtime_config
        base_url = config.base_url if config else settings.llm_base_url
        api_key = config.api_key if config else settings.llm_api_key
        models = config.models if config else settings.llm_models
        provider = config.provider if config else "openai"

        if not models:
            return None
        if self._requires_api_key(provider) and not api_key:
            return None

        user_prompt = json.dumps(payload, ensure_ascii=False)

        for model in models:
            try:
                result = self._call_chat_completions(
                    provider=provider,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    base_url=base_url,
                    api_key=api_key,
                    temperature=temperature,
                )
                if result:
                    return result
            except Exception:
                continue

        return None

    def _call_chat_completions(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        base_url: str,
        api_key: str,
        temperature: float,
    ) -> dict | None:
        if provider == "anthropic":
            return self._call_anthropic(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
            )
        if provider == "gemini":
            return self._call_gemini(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
            )

        body = {
            "model": model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request = Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(request, timeout=30) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError):
            return None

        content = (
            raw.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not content:
            return None

        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                return None
            return parsed
        except Exception:
            return None

    def _call_anthropic(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        base_url: str,
        api_key: str,
        temperature: float,
    ) -> dict | None:
        body = {
            "model": model,
            "max_tokens": 1200,
            "temperature": temperature,
            "system": f"{system_prompt}\nReturn strict JSON only.",
            "messages": [{"role": "user", "content": user_prompt}],
        }
        request = Request(
            f"{base_url.rstrip('/')}/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=40) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError):
            return None

        text_parts = []
        for block in raw.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text") or ""))
        content = "\n".join(part for part in text_parts if part).strip()
        if not content:
            return None
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def _call_gemini(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        base_url: str,
        api_key: str,
        temperature: float,
    ) -> dict | None:
        body = {
            "system_instruction": {"parts": [{"text": f"{system_prompt}\nReturn strict JSON only."}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        endpoint = (
            f"{base_url.rstrip('/')}/v1beta/models/{quote_plus(model)}:generateContent"
            f"?key={quote_plus(api_key)}"
        )
        request = Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=40) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError):
            return None

        text = (
            raw.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
