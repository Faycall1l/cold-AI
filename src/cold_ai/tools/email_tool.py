from __future__ import annotations

from typing import Any

from ..services.email_provider import ConsoleEmailProvider, SMTPEmailProvider
from .base import ToolResult


class EmailTool:
    name = "email"

    def run(self, payload: dict[str, Any]) -> ToolResult:
        to_email = str(payload.get("to") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        body = str(payload.get("body") or "").strip()
        dry_run = bool(payload.get("dry_run", True))

        if not to_email or not subject or not body:
            return ToolResult(ok=False, tool=self.name, data={}, error="Missing to/subject/body")

        provider = ConsoleEmailProvider() if dry_run else SMTPEmailProvider()
        try:
            provider.send(to_email, subject, body)
            return ToolResult(ok=True, tool=self.name, data={"to": to_email, "dry_run": dry_run})
        except Exception as exc:
            return ToolResult(ok=False, tool=self.name, data={"to": to_email, "dry_run": dry_run}, error=str(exc))
