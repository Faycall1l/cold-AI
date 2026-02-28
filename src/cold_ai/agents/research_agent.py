from __future__ import annotations

import json
import re
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from ..config import settings

SPECIALTY_RESOURCE_MAP = {
    "dentiste": "https://www.who.int/news-room/fact-sheets/detail/oral-health",
    "cardio": "https://www.who.int/health-topics/cardiovascular-diseases",
    "nutrition": "https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
    "diab": "https://www.who.int/health-topics/diabetes",
    "pedi": "https://www.who.int/health-topics/child-health",
}


class ResearchAgent:
    def research(self, lead: dict) -> dict:
        specialty = (lead.get("specialty") or "").lower()
        default_resource = "https://www.who.int/health-topics/digital-health"
        resource_link = next(
            (
                url
                for keyword, url in SPECIALTY_RESOURCE_MAP.items()
                if keyword in specialty
            ),
            default_resource,
        )

        web_snippet = ""
        source_link = ""

        if settings.enable_web_research:
            query = " ".join(
                value
                for value in [
                    lead.get("full_name") or "",
                    lead.get("specialty") or "",
                    lead.get("city") or "",
                    "doctor Algeria",
                ]
                if value
            )
            snippet, link = self._duckduckgo_snippet(query)
            web_snippet = snippet
            source_link = link

        return {
            "resource_link": resource_link,
            "research_snippet": web_snippet,
            "research_source_link": source_link,
        }

    def _duckduckgo_snippet(self, query: str) -> tuple[str, str]:
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
            return snippet[:280], link
        except Exception:
            return "", ""
