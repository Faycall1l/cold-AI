from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import settings


class LLMRouter:
    def available(self) -> bool:
        return bool(settings.llm_api_key and settings.llm_models)

    def rewrite_email(self, payload: dict) -> dict | None:
        if not self.available():
            return None

        system_prompt = (
            "You are a sales outreach rewriting assistant. "
            "Rewrite for a human, concise, credible tone. Avoid hype, spammy phrasing, and robotic language. "
            "Return strict JSON with keys: subject, body, confidence. "
            "confidence is a float between 0 and 1."
        )
        user_prompt = json.dumps(payload, ensure_ascii=False)

        for model in settings.llm_models:
            try:
                result = self._call_chat_completions(model, system_prompt, user_prompt)
                if result:
                    return result
            except Exception:
                continue

        return None

    def _call_chat_completions(self, model: str, system_prompt: str, user_prompt: str) -> dict | None:
        body = {
            "model": model,
            "temperature": 0.6,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        request = Request(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.llm_api_key}",
            },
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
