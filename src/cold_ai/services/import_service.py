from __future__ import annotations

import re
import unicodedata
from typing import Any

from ..agents.orchestrator_agent import OrchestratorAgent
from ..repositories import LeadRepository
from .csv_io import read_csv_rows

ALIASES = {
    "email": ["email", "mail"],
    "phone": ["phone", "telephone", "tel", "mobile", "gsm", "numero", "numero de telephone"],
    "full_name": [
        "full_name",
        "name",
        "doctor_name",
        "nom",
        "nom francais",
    ],
    "specialty": [
        "specialty",
        "speciality",
        "specialite",
        "specialites",
        "specialite s",
    ],
    "city": ["city", "ville", "commune", "wilaya"],
    "address": ["address", "adresse", "rue adresse"],
    "commune": ["commune"],
    "wilaya": ["wilaya"],
}


def _normalize_phone(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    has_plus = text.startswith("+")
    digits = re.sub(r"\D+", "", text)
    if not digits:
        return ""
    if has_plus:
        return f"+{digits}"
    return digits


def _synthetic_email_for_phone(phone: str) -> str:
    normalized = re.sub(r"\D+", "", phone)
    return f"phone-{normalized}@no-email.invalid"


def _normalize_key(value: str) -> str:
    text = str(value).replace("\ufeff", "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _first_present(row: dict[str, Any], keys: list[str]) -> str:
    lowered = {_normalize_key(str(k)): v for k, v in row.items()}
    for key in keys:
        value = lowered.get(_normalize_key(key))
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def import_leads(csv_path) -> tuple[int, int]:
    rows = read_csv_rows(csv_path)
    orchestrator = OrchestratorAgent()
    normalized: list[dict] = []

    for row in rows:
        email = _first_present(row, ALIASES["email"]).lower()
        phone = _normalize_phone(_first_present(row, ALIASES["phone"]))
        if not email and not phone:
            continue
        if not email and phone:
            email = _synthetic_email_for_phone(phone)

        city = _first_present(row, ALIASES["city"])
        commune = _first_present(row, ALIASES["commune"])
        wilaya = _first_present(row, ALIASES["wilaya"])
        if not city:
            city = " / ".join([value for value in [commune, wilaya] if value])

        lead = {
            "email": email,
            "phone": phone,
            "full_name": _first_present(row, ALIASES["full_name"]),
            "specialty": _first_present(row, ALIASES["specialty"]),
            "city": city,
            "address": _first_present(row, ALIASES["address"]),
        }
        normalized.append(orchestrator.prepare_lead(lead))

    repository = LeadRepository()
    return repository.upsert_many(normalized)
