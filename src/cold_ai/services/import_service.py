from __future__ import annotations

from typing import Any

from ..agents.orchestrator_agent import OrchestratorAgent
from ..repositories import LeadRepository
from .csv_io import read_csv_rows

ALIASES = {
    "email": ["email", "mail"],
    "full_name": ["full_name", "name", "doctor_name", "nom"],
    "specialty": ["specialty", "speciality", "specialite"],
    "city": ["city", "ville"],
    "address": ["address", "adresse"],
}


def _first_present(row: dict[str, Any], keys: list[str]) -> str:
    lowered = {str(k).lower().strip(): v for k, v in row.items()}
    for key in keys:
        value = lowered.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def import_leads(csv_path) -> tuple[int, int]:
    rows = read_csv_rows(csv_path)
    orchestrator = OrchestratorAgent()
    normalized: list[dict] = []

    for row in rows:
        email = _first_present(row, ALIASES["email"]).lower()
        if not email:
            continue
        lead = {
            "email": email,
            "full_name": _first_present(row, ALIASES["full_name"]),
            "specialty": _first_present(row, ALIASES["specialty"]),
            "city": _first_present(row, ALIASES["city"]),
            "address": _first_present(row, ALIASES["address"]),
        }
        normalized.append(orchestrator.prepare_lead(lead))

    repository = LeadRepository()
    return repository.upsert_many(normalized)
