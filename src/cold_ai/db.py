from __future__ import annotations

import sqlite3
from pathlib import Path

from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_connection() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                first_name TEXT,
                last_name TEXT,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                specialty TEXT,
                city TEXT,
                address TEXT,
                source_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                purpose TEXT,
                channel TEXT NOT NULL DEFAULT 'email',
                subject_template TEXT NOT NULL,
                body_template TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                lead_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                scheduled_at TEXT,
                approved_at TEXT,
                sent_at TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(campaign_id, lead_id),
                FOREIGN KEY(campaign_id) REFERENCES campaigns(id),
                FOREIGN KEY(lead_id) REFERENCES leads(id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id INTEGER,
                event_type TEXT NOT NULL,
                payload TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(draft_id) REFERENCES drafts(id)
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS template_library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_key TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_key TEXT NOT NULL UNIQUE,
                llm_provider TEXT NOT NULL DEFAULT 'openai',
                llm_base_url TEXT,
                llm_api_key TEXT,
                llm_models_json TEXT,
                enable_web_research INTEGER NOT NULL DEFAULT 0,
                enable_llm_rewrite INTEGER NOT NULL DEFAULT 0,
                prompt_search TEXT,
                prompt_routing TEXT,
                prompt_supervisor TEXT,
                prompt_rewrite TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS outreach_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_key TEXT NOT NULL,
                channel TEXT NOT NULL,
                purpose TEXT,
                specialty TEXT,
                pattern_text TEXT NOT NULL,
                quality_score REAL NOT NULL DEFAULT 0.5,
                source_event TEXT NOT NULL,
                usage_count INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        campaign_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(campaigns)").fetchall()
        }
        if "purpose" not in campaign_columns:
            conn.execute("ALTER TABLE campaigns ADD COLUMN purpose TEXT")
        if "channel" not in campaign_columns:
            conn.execute("ALTER TABLE campaigns ADD COLUMN channel TEXT NOT NULL DEFAULT 'email'")

        lead_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(leads)").fetchall()
        }
        if "phone" not in lead_columns:
            conn.execute("ALTER TABLE leads ADD COLUMN phone TEXT")

        agent_settings_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(agent_settings)").fetchall()
        }
        if "llm_provider" not in agent_settings_columns:
            conn.execute(
                "ALTER TABLE agent_settings ADD COLUMN llm_provider TEXT NOT NULL DEFAULT 'openai'"
            )

        outreach_memory_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(outreach_memory)").fetchall()
        }
        if outreach_memory_columns and "usage_count" not in outreach_memory_columns:
            conn.execute("ALTER TABLE outreach_memory ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0")
        if outreach_memory_columns and "last_used_at" not in outreach_memory_columns:
            conn.execute("ALTER TABLE outreach_memory ADD COLUMN last_used_at TEXT")

        existing = conn.execute(
            "SELECT id FROM users WHERE lower(email) = lower(?)",
            ("mock.admin@cold-ai.com",),
        ).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO users (email, password_hash, full_name)
                VALUES (?, ?, ?)
                """,
                ("mock.admin@cold-ai.com", pwd_context.hash("MockAdmin123!"), "Mock Admin"),
            )
