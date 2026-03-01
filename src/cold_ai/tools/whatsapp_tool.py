from __future__ import annotations

from typing import Any

from ..services.whatsapp_provider import ConsoleWhatsAppProvider, UnconfiguredWhatsAppProvider
from .base import ToolResult


class WhatsAppTool:
    name = "whatsapp"

    def run(self, payload: dict[str, Any]) -> ToolResult:
        to_phone = str(payload.get("to") or "").strip()
        body = str(payload.get("body") or "").strip()
        dry_run = bool(payload.get("dry_run", True))

        if not to_phone or not body:
            return ToolResult(ok=False, tool=self.name, data={}, error="Missing to/body")

        provider = ConsoleWhatsAppProvider() if dry_run else UnconfiguredWhatsAppProvider()
        try:
            provider.send(to_phone, body)
            return ToolResult(ok=True, tool=self.name, data={"to": to_phone, "dry_run": dry_run})
        except Exception as exc:
            return ToolResult(ok=False, tool=self.name, data={"to": to_phone, "dry_run": dry_run}, error=str(exc))
