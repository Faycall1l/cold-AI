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


settings = Settings()
