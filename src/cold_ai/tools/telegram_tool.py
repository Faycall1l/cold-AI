from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

from ..config import settings
from .base import ToolResult


class TelegramTool:
    name = "telegram"

    def run(self, payload: dict[str, Any]) -> ToolResult:
        text = str(payload.get("text") or payload.get("body") or "").strip()
        chat_id = str(payload.get("chat_id") or settings.telegram_default_chat_id or "").strip()
        dry_run = bool(payload.get("dry_run", True))

        if not text:
            return ToolResult(ok=False, tool=self.name, data={}, error="Missing text/body")
        if not chat_id:
            return ToolResult(ok=False, tool=self.name, data={}, error="Missing chat_id")

        if dry_run:
            print("=" * 80)
            print(f"TELEGRAM TO: {chat_id}")
            print(text)
            print("=" * 80)
            return ToolResult(ok=True, tool=self.name, data={"chat_id": chat_id, "dry_run": True})

        if not settings.telegram_bot_token:
            return ToolResult(ok=False, tool=self.name, data={"chat_id": chat_id}, error="Telegram bot token not configured")

        try:
            endpoint = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            payload_json = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
            req = Request(endpoint, data=payload_json, headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=10) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            return ToolResult(ok=True, tool=self.name, data={"chat_id": chat_id, "response": raw})
        except Exception as exc:
            return ToolResult(ok=False, tool=self.name, data={"chat_id": chat_id}, error=str(exc))
