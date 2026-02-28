from __future__ import annotations

import re


BLOCKED_TERMS = (
    "nigger",
    "nigga",
    "faggot",
    "kike",
    "spic",
    "chink",
)


class GuardrailError(ValueError):
    pass


def _normalize_single_line(text: str) -> str:
    return " ".join(text.strip().split())


def _normalize_multiline(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


def _contains_blocked_terms(text: str) -> list[str]:
    lowered = text.lower()
    matched: list[str] = []
    for term in BLOCKED_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            matched.append(term)
    return matched


def _validate_text(
    field_name: str,
    value: str,
    *,
    min_len: int,
    max_len: int,
    allow_empty: bool = False,
    multiline: bool = False,
) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise GuardrailError(f"{field_name} must be a string")

    cleaned = _normalize_multiline(value) if multiline else _normalize_single_line(value)

    if not cleaned and allow_empty:
        return ""
    if len(cleaned) < min_len:
        raise GuardrailError(f"{field_name} must be at least {min_len} characters")
    if len(cleaned) > max_len:
        raise GuardrailError(f"{field_name} must be at most {max_len} characters")

    blocked = _contains_blocked_terms(cleaned)
    if blocked:
        raise GuardrailError(f"{field_name} contains blocked language: {', '.join(blocked)}")

    return cleaned


def validate_campaign_inputs(name: str, purpose: str, subject_template: str, body_template: str) -> dict[str, str]:
    validated_name = _validate_text("Campaign name", name, min_len=3, max_len=120)
    validated_purpose = _validate_text(
        "Campaign purpose",
        purpose,
        min_len=0,
        max_len=280,
        allow_empty=True,
    )
    validated_subject = _validate_text("Subject template", subject_template, min_len=5, max_len=240)
    validated_body = _validate_text(
        "Body template",
        body_template,
        min_len=20,
        max_len=8000,
        multiline=True,
    )
    return {
        "name": validated_name,
        "purpose": validated_purpose,
        "subject_template": validated_subject,
        "body_template": validated_body,
    }


def validate_draft_content(subject: str, body: str) -> dict[str, str]:
    validated_subject = _validate_text("Subject", subject, min_len=3, max_len=240)
    validated_body = _validate_text("Body", body, min_len=20, max_len=8000, multiline=True)
    return {"subject": validated_subject, "body": validated_body}
