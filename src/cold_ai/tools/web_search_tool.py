from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from .base import ToolResult


class WebSearchTool:
    name = "web_search"

    def run(self, payload: dict[str, Any]) -> ToolResult:
        query = str(payload.get("query") or "").strip()
        if not query:
            return ToolResult(ok=False, tool=self.name, data={}, error="Missing query")

        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=8) as response:
                html = response.read().decode("utf-8", errors="ignore")

            link_match = re.search(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', html)
            snippet_match = re.search(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html, flags=re.S)
            if not snippet_match:
                snippet_match = re.search(r'<div[^>]+class="result__snippet"[^>]*>(.*?)</div>', html, flags=re.S)

            link = link_match.group(1).strip() if link_match else ""
            snippet = (
                re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", snippet_match.group(1))).strip()
                if snippet_match
                else ""
            )
            return ToolResult(
                ok=True,
                tool=self.name,
                data={"query": query, "snippet": snippet[:280], "link": link},
            )
        except Exception as exc:
            return ToolResult(ok=False, tool=self.name, data={"query": query}, error=str(exc))
