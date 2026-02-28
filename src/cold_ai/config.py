from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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

    oauth_google_client_id: str | None = os.getenv("COLD_AI_OAUTH_GOOGLE_CLIENT_ID")
    oauth_google_client_secret: str | None = os.getenv("COLD_AI_OAUTH_GOOGLE_CLIENT_SECRET")


settings = Settings()
