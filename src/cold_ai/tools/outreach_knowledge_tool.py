from __future__ import annotations

from typing import Any

from ..services.outreach_knowledge_base import (
    build_outreach_knowledge_context,
    search_outreach_knowledge,
)
from .base import ToolResult


class OutreachKnowledgeTool:
    name = "outreach_knowledge"

    def run(self, payload: dict[str, Any]) -> ToolResult:
        mode = str(payload.get("mode") or "context").strip().lower()

        if mode == "search":
            query = str(payload.get("query") or "").strip()
            if not query:
                return ToolResult(ok=False, tool=self.name, data={}, error="Missing query")
            limit = int(payload.get("limit") or 5)
            return ToolResult(
                ok=True,
                tool=self.name,
                data={
                    "mode": "search",
                    "query": query,
                    "results": search_outreach_knowledge(query, limit=limit),
                },
            )

        channel = str(payload.get("channel") or "email")
        purpose = str(payload.get("purpose") or "")
        specialty = str(payload.get("specialty") or "")

        context = build_outreach_knowledge_context(
            channel=channel,
            purpose=purpose,
            specialty=specialty,
        )
        return ToolResult(ok=True, tool=self.name, data={"mode": "context", "context": context})
