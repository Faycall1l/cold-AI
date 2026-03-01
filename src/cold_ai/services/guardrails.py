from __future__ import annotations

import re


SUPPORTED_LLM_PROVIDERS = {
    "openai",
    "openrouter",
    "groq",
    "together",
    "ollama",
    "vllm",
    "anthropic",
    "gemini",
}


PROVIDER_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "ollama": "http://127.0.0.1:11434/v1",
    "vllm": "http://127.0.0.1:8000/v1",
    "anthropic": "https://api.anthropic.com",
    "gemini": "https://generativelanguage.googleapis.com",
}


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


def validate_template_library_entry(title: str, category: str, content: str) -> dict[str, str]:
    validated_title = _validate_text("Template title", title, min_len=3, max_len=120)
    validated_category = _normalize_single_line(category).lower()
    allowed_categories = {"script", "product", "service"}
    if validated_category not in allowed_categories:
        raise GuardrailError("Category must be one of: script, product, service")
    validated_content = _validate_text(
        "Template content",
        content,
        min_len=10,
        max_len=8000,
        multiline=True,
    )
    return {
        "title": validated_title,
        "category": validated_category,
        "content": validated_content,
    }


def validate_campaign_channel(channel: str) -> str:
    cleaned = _normalize_single_line(channel).lower()
    if cleaned not in {"email", "whatsapp"}:
        raise GuardrailError("Campaign channel must be one of: email, whatsapp")
    return cleaned


def validate_agent_settings_payload(payload: dict) -> dict:
    llm_provider = _normalize_single_line(str(payload.get("llm_provider") or "openai")).lower()
    if llm_provider not in SUPPORTED_LLM_PROVIDERS:
        raise GuardrailError(
            "LLM provider must be one of: " + ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
        )

    default_base_url = PROVIDER_DEFAULT_BASE_URLS.get(llm_provider, "")
    llm_base_url = _validate_text(
        "LLM base URL",
        str(payload.get("llm_base_url") or default_base_url),
        min_len=8,
        max_len=300,
    )
    llm_api_key = str(payload.get("llm_api_key") or "").strip()
    if llm_api_key and len(llm_api_key) > 400:
        raise GuardrailError("LLM API key is too long")

    raw_models = payload.get("llm_models") or []
    if isinstance(raw_models, str):
        models = [m.strip() for m in raw_models.split(",") if m.strip()]
    elif isinstance(raw_models, list):
        models = [str(m).strip() for m in raw_models if str(m).strip()]
    else:
        raise GuardrailError("LLM models must be a list or comma-separated string")

    if len(models) > 8:
        raise GuardrailError("At most 8 models are allowed")

    prompt_search = _validate_text(
        "Search agent prompt",
        str(payload.get("prompt_search") or ""),
        min_len=20,
        max_len=4000,
        multiline=True,
    )
    prompt_routing = _validate_text(
        "Routing agent prompt",
        str(payload.get("prompt_routing") or ""),
        min_len=20,
        max_len=4000,
        multiline=True,
    )
    prompt_supervisor = _validate_text(
        "Supervisor agent prompt",
        str(payload.get("prompt_supervisor") or ""),
        min_len=20,
        max_len=4000,
        multiline=True,
    )
    prompt_rewrite = _validate_text(
        "Rewrite agent prompt",
        str(payload.get("prompt_rewrite") or ""),
        min_len=20,
        max_len=4000,
        multiline=True,
    )

    return {
        "llm_provider": llm_provider,
        "llm_base_url": llm_base_url,
        "llm_api_key": llm_api_key,
        "llm_models": models,
        "enable_web_research": bool(payload.get("enable_web_research", False)),
        "enable_llm_rewrite": bool(payload.get("enable_llm_rewrite", False)),
        "prompt_search": prompt_search,
        "prompt_routing": prompt_routing,
        "prompt_supervisor": prompt_supervisor,
        "prompt_rewrite": prompt_rewrite,
    }
