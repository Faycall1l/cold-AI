from __future__ import annotations

from pathlib import Path

from ..repositories import CampaignRepository
from .guardrails import validate_campaign_channel, validate_campaign_inputs


def create_campaign(
    name: str,
    subject_template_path: Path,
    body_template_path: Path,
    purpose: str = "",
    channel: str = "email",
) -> int:
    subject_template = subject_template_path.read_text(encoding="utf-8")
    body_template = body_template_path.read_text(encoding="utf-8")
    validated = validate_campaign_inputs(name, purpose, subject_template, body_template)
    validated_channel = validate_campaign_channel(channel)
    repository = CampaignRepository()
    return repository.create(
        validated["name"],
        validated["purpose"] or None,
        validated_channel,
        validated["subject_template"],
        validated["body_template"],
    )
