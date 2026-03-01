from __future__ import annotations

import json
from datetime import datetime, timezone

from .db import get_connection


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LeadRepository:
    def upsert_many(self, leads: list[dict]) -> tuple[int, int]:
        inserted = 0
        skipped = 0
        with get_connection() as conn:
            for lead in leads:
                try:
                    conn.execute(
                        """
                        INSERT INTO leads (full_name, first_name, last_name, email, phone, specialty, city, address, source_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            lead.get("full_name"),
                            lead.get("first_name"),
                            lead.get("last_name"),
                            lead["email"],
                            lead.get("phone"),
                            lead.get("specialty"),
                            lead.get("city"),
                            lead.get("address"),
                            lead.get("source_hash"),
                        ),
                    )
                    inserted += 1
                except Exception:
                    skipped += 1
        return inserted, skipped

    def list_for_drafting(self, limit: int, channel: str) -> list[dict]:
        if channel == "whatsapp":
            where_clause = "l.phone IS NOT NULL AND trim(l.phone) != ''"
        else:
            where_clause = "l.email IS NOT NULL AND lower(l.email) NOT LIKE '%@no-email.invalid'"

        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT l.*
                FROM leads l
                WHERE {where_clause}
                ORDER BY l.id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_by_id(self, lead_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return dict(row) if row else None


class CampaignRepository:
    def create(self, name: str, purpose: str | None, channel: str, subject_template: str, body_template: str) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO campaigns (name, purpose, channel, subject_template, body_template)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, purpose, channel, subject_template, body_template),
            )
            return int(cursor.lastrowid)

    def get(self, campaign_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM campaigns
                ORDER BY id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]


class DraftRepository:
    def create_or_ignore(self, campaign_id: int, lead_id: int, subject: str, body: str) -> bool:
        with get_connection() as conn:
            result = conn.execute(
                """
                INSERT OR IGNORE INTO drafts (campaign_id, lead_id, subject, body, status)
                VALUES (?, ?, ?, ?, 'draft')
                """,
                (campaign_id, lead_id, subject, body),
            )
            return result.rowcount > 0

    def list_for_campaign(self, campaign_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT d.*, l.email, l.phone, l.full_name, l.specialty, l.city, c.channel
                FROM drafts d
                JOIN leads l ON l.id = d.lead_id
                JOIN campaigns c ON c.id = d.campaign_id
                WHERE d.campaign_id = ?
                ORDER BY d.id ASC
                """,
                (campaign_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def approve_and_schedule(self, draft_id: int, scheduled_at: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE drafts
                SET status = 'approved', approved_at = ?, scheduled_at = ?
                WHERE id = ?
                """,
                (utc_now_iso(), scheduled_at, draft_id),
            )

    def mark_rejected(self, draft_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE drafts SET status = 'rejected' WHERE id = ?",
                (draft_id,),
            )

    def update_content(self, draft_id: int, subject: str, body: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE drafts
                SET subject = ?, body = ?
                WHERE id = ?
                """,
                (subject, body, draft_id),
            )

    def list_due(self, now_iso: str, campaign_id: int | None = None) -> list[dict]:
        where_campaign = "AND d.campaign_id = ?" if campaign_id is not None else ""
        params: tuple = (now_iso, campaign_id) if campaign_id is not None else (now_iso,)

        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT d.*, l.email, l.phone, c.channel
                      , l.specialty, c.purpose
                FROM drafts d
                JOIN leads l ON l.id = d.lead_id
                JOIN campaigns c ON c.id = d.campaign_id
                WHERE d.status = 'approved'
                  AND d.scheduled_at IS NOT NULL
                  AND d.scheduled_at <= ?
                  {where_campaign}
                ORDER BY d.scheduled_at ASC
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_sent(self, draft_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE drafts
                SET status = 'sent', sent_at = ?, error_message = NULL
                WHERE id = ?
                """,
                (utc_now_iso(), draft_id),
            )

    def mark_failed(self, draft_id: int, error: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE drafts
                SET status = 'failed', error_message = ?
                WHERE id = ?
                """,
                (error[:1000], draft_id),
            )


class EventRepository:
    def log(self, event_type: str, payload: dict, draft_id: int | None = None) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO events (draft_id, event_type, payload)
                VALUES (?, ?, ?)
                """,
                (draft_id, event_type, json.dumps(payload, ensure_ascii=False)),
            )


class UserRepository:
    def create(self, email: str, password_hash: str, full_name: str | None = None) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (email, password_hash, full_name)
                VALUES (?, ?, ?)
                """,
                (email, password_hash, full_name),
            )
            return int(cursor.lastrowid)

    def get_by_email(self, email: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE lower(email) = lower(?)",
                (email,),
            ).fetchone()
        return dict(row) if row else None

    def get_by_id(self, user_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def update_password_hash(self, user_id: int, password_hash: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )


class TemplateLibraryRepository:
    def list_by_owner(self, owner_key: str) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM template_library
                WHERE owner_key = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (owner_key,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create(self, owner_key: str, title: str, category: str, content: str) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO template_library (owner_key, title, category, content)
                VALUES (?, ?, ?, ?)
                """,
                (owner_key, title, category, content),
            )
            return int(cursor.lastrowid)

    def get_by_id_for_owner(self, entry_id: int, owner_key: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM template_library WHERE id = ? AND owner_key = ?",
                (entry_id, owner_key),
            ).fetchone()
        return dict(row) if row else None

    def update_for_owner(self, entry_id: int, owner_key: str, title: str, category: str, content: str) -> bool:
        with get_connection() as conn:
            result = conn.execute(
                """
                UPDATE template_library
                SET title = ?, category = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND owner_key = ?
                """,
                (title, category, content, entry_id, owner_key),
            )
            return result.rowcount > 0

    def delete_for_owner(self, entry_id: int, owner_key: str) -> bool:
        with get_connection() as conn:
            result = conn.execute(
                "DELETE FROM template_library WHERE id = ? AND owner_key = ?",
                (entry_id, owner_key),
            )
            return result.rowcount > 0


class AgentSettingsRepository:
    def get_by_owner(self, owner_key: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM agent_settings WHERE owner_key = ?",
                (owner_key,),
            ).fetchone()
        if not row:
            return None
        payload = dict(row)
        raw_models = payload.get("llm_models_json") or "[]"
        try:
            payload["llm_models"] = json.loads(raw_models)
        except Exception:
            payload["llm_models"] = []
        return payload

    def upsert_for_owner(
        self,
        owner_key: str,
        llm_provider: str,
        llm_base_url: str,
        llm_api_key: str | None,
        llm_models: list[str],
        enable_web_research: bool,
        enable_llm_rewrite: bool,
        prompt_search: str,
        prompt_routing: str,
        prompt_supervisor: str,
        prompt_rewrite: str,
    ) -> None:
        existing = self.get_by_owner(owner_key)
        effective_key = llm_api_key if llm_api_key is not None else (existing or {}).get("llm_api_key")

        with get_connection() as conn:
            if existing:
                conn.execute(
                    """
                    UPDATE agent_settings
                    SET llm_provider = ?,
                        llm_base_url = ?,
                        llm_api_key = ?,
                        llm_models_json = ?,
                        enable_web_research = ?,
                        enable_llm_rewrite = ?,
                        prompt_search = ?,
                        prompt_routing = ?,
                        prompt_supervisor = ?,
                        prompt_rewrite = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE owner_key = ?
                    """,
                    (
                        llm_provider,
                        llm_base_url,
                        effective_key,
                        json.dumps(llm_models, ensure_ascii=False),
                        1 if enable_web_research else 0,
                        1 if enable_llm_rewrite else 0,
                        prompt_search,
                        prompt_routing,
                        prompt_supervisor,
                        prompt_rewrite,
                        owner_key,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO agent_settings (
                        owner_key,
                        llm_provider,
                        llm_base_url,
                        llm_api_key,
                        llm_models_json,
                        enable_web_research,
                        enable_llm_rewrite,
                        prompt_search,
                        prompt_routing,
                        prompt_supervisor,
                        prompt_rewrite
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        owner_key,
                        llm_provider,
                        llm_base_url,
                        effective_key,
                        json.dumps(llm_models, ensure_ascii=False),
                        1 if enable_web_research else 0,
                        1 if enable_llm_rewrite else 0,
                        prompt_search,
                        prompt_routing,
                        prompt_supervisor,
                        prompt_rewrite,
                    ),
                )


class OutreachMemoryRepository:
    def list_by_owner(
        self,
        owner_key: str,
        limit: int = 20,
        channel: str | None = None,
    ) -> list[dict]:
        with get_connection() as conn:
            if channel and channel.strip():
                rows = conn.execute(
                    """
                    SELECT *
                    FROM outreach_memory
                    WHERE owner_key = ? AND channel = ?
                    ORDER BY quality_score DESC, usage_count DESC, id DESC
                    LIMIT ?
                    """,
                    (owner_key, channel.strip().lower(), max(1, min(limit, 100))),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM outreach_memory
                    WHERE owner_key = ?
                    ORDER BY quality_score DESC, usage_count DESC, id DESC
                    LIMIT ?
                    """,
                    (owner_key, max(1, min(limit, 100))),
                ).fetchall()
        return [dict(row) for row in rows]

    def list_for_context(
        self,
        owner_key: str,
        channel: str,
        purpose: str | None,
        specialty: str | None,
        limit: int = 5,
    ) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM outreach_memory
                WHERE owner_key = ?
                  AND channel = ?
                  AND (? IS NULL OR purpose = ? OR purpose = '')
                  AND (? IS NULL OR specialty = ? OR specialty = '')
                ORDER BY quality_score DESC, usage_count DESC, id DESC
                LIMIT ?
                """,
                (
                    owner_key,
                    channel,
                    purpose,
                    purpose,
                    specialty,
                    specialty,
                    limit,
                ),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_memory(
        self,
        owner_key: str,
        channel: str,
        purpose: str,
        specialty: str,
        pattern_text: str,
        quality_score: float,
        source_event: str,
    ) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO outreach_memory (
                    owner_key,
                    channel,
                    purpose,
                    specialty,
                    pattern_text,
                    quality_score,
                    source_event,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    owner_key,
                    channel,
                    purpose,
                    specialty,
                    pattern_text[:600],
                    max(0.0, min(1.0, quality_score)),
                    source_event,
                ),
            )

    def mark_used(self, memory_ids: list[int]) -> None:
        if not memory_ids:
            return
        with get_connection() as conn:
            for memory_id in memory_ids:
                conn.execute(
                    """
                    UPDATE outreach_memory
                    SET usage_count = usage_count + 1,
                        last_used_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (memory_id,),
                )

    def clear_by_owner(self, owner_key: str, channel: str | None = None) -> int:
        with get_connection() as conn:
            if channel and channel.strip():
                result = conn.execute(
                    "DELETE FROM outreach_memory WHERE owner_key = ? AND channel = ?",
                    (owner_key, channel.strip().lower()),
                )
            else:
                result = conn.execute(
                    "DELETE FROM outreach_memory WHERE owner_key = ?",
                    (owner_key,),
                )
            return int(result.rowcount or 0)
