from __future__ import annotations

from typing import Any

from ..repositories import OutreachMemoryRepository
from .base import ToolResult


class OutreachMemoryTool:
    name = "outreach_memory"

    def run(self, payload: dict[str, Any]) -> ToolResult:
        owner_key = str(payload.get("owner_key") or "global")
        channel = str(payload.get("channel") or "email").strip().lower() or "email"
        purpose = str(payload.get("purpose") or "").strip() or None
        specialty = str(payload.get("specialty") or "").strip() or None
        limit = int(payload.get("limit") or 5)

        rows = OutreachMemoryRepository().list_for_context(
            owner_key=owner_key,
            channel=channel,
            purpose=purpose,
            specialty=specialty,
            limit=limit,
        )
        return ToolResult(ok=True, tool=self.name, data={"items": rows, "count": len(rows)})
