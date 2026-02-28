from __future__ import annotations

from pathlib import Path


class SpecialtyTemplateRouter:
    def __init__(self) -> None:
        self.base_dir = Path("templates/specialties")
        self.specialty_map = {
            "dent": "dentiste",
            "cardio": "cardiology",
            "pedi": "pediatrics",
            "nutrition": "nutrition",
            "diab": "diabetes",
        }

    def select(self, specialty: str, fallback_subject: str, fallback_body: str) -> tuple[str, str, str]:
        specialty_lower = (specialty or "").lower()
        slug = next(
            (value for key, value in self.specialty_map.items() if key in specialty_lower),
            "",
        )
        if not slug:
            return fallback_subject, fallback_body, "campaign_default"

        subject_path = self.base_dir / f"subject_{slug}.txt"
        body_path = self.base_dir / f"body_{slug}.txt"
        if not subject_path.exists() or not body_path.exists():
            return fallback_subject, fallback_body, "campaign_default"

        return (
            subject_path.read_text(encoding="utf-8"),
            body_path.read_text(encoding="utf-8"),
            slug,
        )
