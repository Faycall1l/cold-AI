from __future__ import annotations

from jinja2 import Environment, StrictUndefined


class CopywriterAgent:
    def __init__(self) -> None:
        self.env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)

    def draft(self, subject_template: str, body_template: str, context: dict) -> tuple[str, str]:
        subject = self.env.from_string(subject_template).render(**context).strip()
        body = self.env.from_string(body_template).render(**context).strip()
        return subject, body
