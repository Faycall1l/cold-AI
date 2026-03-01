from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _csv_env(name: str, default: str = "") -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path("data/cold_ai.db")
    export_dir: Path = Path("data/exports")

    smtp_host: str | None = os.getenv("COLD_AI_SMTP_HOST")
    smtp_port: int = int(os.getenv("COLD_AI_SMTP_PORT", "587"))
    smtp_user: str | None = os.getenv("COLD_AI_SMTP_USER")
    smtp_password: str | None = os.getenv("COLD_AI_SMTP_PASSWORD")
    smtp_from: str | None = os.getenv("COLD_AI_SMTP_FROM")
    smtp_starttls: bool = os.getenv("COLD_AI_SMTP_STARTTLS", "true").lower() == "true"

    enable_web_research: bool = os.getenv("COLD_AI_ENABLE_WEB_RESEARCH", "false").lower() == "true"
    enable_llm_rewrite: bool = os.getenv("COLD_AI_ENABLE_LLM_REWRITE", "false").lower() == "true"

    llm_base_url: str = os.getenv("COLD_AI_LLM_BASE_URL", "https://api.openai.com/v1")
    llm_api_key: str | None = os.getenv("COLD_AI_LLM_API_KEY")
    llm_models: tuple[str, ...] = tuple(
        model.strip()
        for model in os.getenv("COLD_AI_LLM_MODELS", "gpt-4o-mini,gpt-4.1-mini").split(",")
        if model.strip()
    )

    app_base_url: str = os.getenv("COLD_AI_APP_BASE_URL", "http://127.0.0.1:8000")
    session_secret: str = os.getenv("COLD_AI_SESSION_SECRET", "change-me-in-production")
    session_max_age_seconds: int = int(os.getenv("COLD_AI_SESSION_MAX_AGE_SECONDS", "86400"))

    oauth_google_client_id: str | None = os.getenv("COLD_AI_OAUTH_GOOGLE_CLIENT_ID")
    oauth_google_client_secret: str | None = os.getenv("COLD_AI_OAUTH_GOOGLE_CLIENT_SECRET")

    telegram_bot_token: str | None = os.getenv("COLD_AI_TELEGRAM_BOT_TOKEN")
    telegram_default_chat_id: str | None = os.getenv("COLD_AI_TELEGRAM_DEFAULT_CHAT_ID")

    tool_profile: str = os.getenv("COLD_AI_TOOL_PROFILE", "messaging").strip().lower()
    tools_allow: tuple[str, ...] = _csv_env("COLD_AI_TOOLS_ALLOW")
    tools_deny: tuple[str, ...] = _csv_env("COLD_AI_TOOLS_DENY")

    tool_loop_detection_enabled: bool = os.getenv(
        "COLD_AI_TOOL_LOOP_DETECTION_ENABLED", "true"
    ).lower() == "true"
    tool_loop_history_size: int = int(os.getenv("COLD_AI_TOOL_LOOP_HISTORY_SIZE", "30"))
    tool_loop_warning_threshold: int = int(
        os.getenv("COLD_AI_TOOL_LOOP_WARNING_THRESHOLD", "6")
    )
    tool_loop_critical_threshold: int = int(
        os.getenv("COLD_AI_TOOL_LOOP_CRITICAL_THRESHOLD", "10")
    )


settings = Settings()
