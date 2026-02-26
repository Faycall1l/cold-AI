from __future__ import annotations

from pathlib import Path

from ..repositories import CampaignRepository


def create_campaign(name: str, subject_template_path: Path, body_template_path: Path) -> int:
    subject_template = subject_template_path.read_text(encoding="utf-8")
    body_template = body_template_path.read_text(encoding="utf-8")
    repository = CampaignRepository()
    return repository.create(name, subject_template, body_template)
