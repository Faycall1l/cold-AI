from __future__ import annotations

import hashlib


class LeadIntelligenceAgent:
    def enrich(self, lead: dict) -> dict:
        full_name = (lead.get("full_name") or "").strip()
        first_name = lead.get("first_name") or ""
        last_name = lead.get("last_name") or ""

        if not full_name and (first_name or last_name):
            full_name = f"{first_name} {last_name}".strip()

        if full_name and not first_name:
            parts = full_name.split()
            first_name = parts[0]
            if len(parts) > 1:
                last_name = " ".join(parts[1:])

        specialty = (lead.get("specialty") or "").strip()
        city = (lead.get("city") or "").strip()

        if specialty and city:
            personalization_hook = f"{specialty} care in {city}"
        elif specialty:
            personalization_hook = f"{specialty} practice"
        elif city:
            personalization_hook = f"healthcare professionals in {city}"
        else:
            personalization_hook = "your medical practice"

        source_hash = hashlib.sha256(
            f"{lead.get('email','')}|{lead.get('address','')}|{specialty}|{city}".encode("utf-8")
        ).hexdigest()

        return {
            **lead,
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "specialty": specialty,
            "city": city,
            "source_hash": source_hash,
            "personalization_hook": personalization_hook,
        }
