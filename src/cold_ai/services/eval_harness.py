from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..agents.reflection_agent import ReflectionAgent
from ..agents.rewrite_agent import RewriteAgent
from ..agents.routing_agent import RoutingAgent
from ..agents.supervisor_agent import SupervisorAgent
from .agent_contracts import (
    validate_reflection,
    validate_rewrite,
    validate_routing_decision,
    validate_search_query,
    validate_supervisor_review,
)


def _build_sample_contexts() -> list[dict]:
    return [
        {
            "full_name": "Dr. Amina B.",
            "specialty": "Dentistry",
            "city": "Algiers",
            "channel": "email",
            "purpose": "lead generation",
            "personalization_hook": "patient reminders and retention",
            "research_snippet": "Local clinics focus on reducing missed follow-up appointments.",
            "memory_patterns": [
                "[email | dentistry | score=0.88] subject_style=Specific benefit + short CTA"
            ],
        },
        {
            "full_name": "Dr. Karim Z.",
            "specialty": "Cardiology",
            "city": "Oran",
            "channel": "whatsapp",
            "purpose": "phone outreach",
            "personalization_hook": "care continuity communication",
            "research_snippet": "Specialists need concise outreach with simple yes/no asks.",
            "memory_patterns": [],
        },
    ]


def _contract_checks() -> dict:
    checks = {
        "search_valid": bool(validate_search_query({"query": "dentist algeria patient reminders"})),
        "search_invalid": bool(validate_search_query({"query": "x"})),
        "routing_valid": bool(
            validate_routing_decision(
                {
                    "routing_angle": "appointment retention",
                    "routing_cta": "Would you be open to a 15-minute call next week?",
                }
            )
        ),
        "routing_invalid": bool(validate_routing_decision({"routing_angle": "x", "routing_cta": "y"})),
        "rewrite_valid": bool(
            validate_rewrite(
                {
                    "subject": "Quick question for your practice",
                    "body": "Hello Doctor, we help clinics improve follow-up communication with clear patient-friendly workflows. Would you be open to a short intro next week?",
                    "confidence": 0.8,
                }
            )
        ),
        "rewrite_invalid": bool(validate_rewrite({"subject": "x", "body": "short", "confidence": 2})),
        "reflection_valid": bool(
            validate_reflection(
                {
                    "subject": "Quick question",
                    "body": "Hello Doctor, this is a structured outreach draft with clear value and one CTA. Would you be open to a 15-minute intro call?",
                    "critique": "Looks concise and specific.",
                    "confidence": 0.7,
                }
            )
        ),
        "reflection_invalid": bool(validate_reflection({"subject": "x", "body": "short", "critique": "", "confidence": 9})),
        "supervisor_valid": bool(
            validate_supervisor_review({"status": "approved", "score": 0.9, "notes": "Good personalization."})
        ),
        "supervisor_invalid": bool(
            validate_supervisor_review({"status": "bad", "score": 1.9, "notes": ""})
        ),
    }

    total = len(checks)
    expected_true = [k for k in checks if k.endswith("_valid")]
    expected_false = [k for k in checks if k.endswith("_invalid")]
    passed = sum(1 for k in expected_true if checks[k]) + sum(1 for k in expected_false if not checks[k])

    return {
        "results": checks,
        "total_checks": total,
        "passed_checks": passed,
        "pass_rate": round((passed / total) if total else 0.0, 3),
    }


def run_agent_evaluation(output_path: Path | None = None) -> dict:
    agent_settings = {
        "enable_web_research": False,
        "enable_llm_rewrite": False,
        "llm_models": ["gpt-4o-mini"],
    }

    routing_agent = RoutingAgent(agent_settings=agent_settings)
    rewrite_agent = RewriteAgent(agent_settings=agent_settings)
    reflection_agent = ReflectionAgent(agent_settings=agent_settings)
    supervisor_agent = SupervisorAgent(agent_settings=agent_settings)

    routing_ok = 0
    rewrite_status_counts: dict[str, int] = {}
    reflection_mode_counts: dict[str, int] = {}
    supervisor_status_counts: dict[str, int] = {}

    sample_subject = "Hello {{ first_name }}"
    sample_body = (
        "Hello Doctor, we help clinics improve patient communication and follow-up cadence "
        "with practical workflows."
    )

    for context in _build_sample_contexts():
        routing = routing_agent.route(context)
        if routing.get("routing_angle") and routing.get("routing_cta"):
            routing_ok += 1

        rewritten_subject, rewritten_body, rewrite_status = rewrite_agent.maybe_rewrite(
            sample_subject,
            sample_body,
            context,
        )
        rewrite_status_counts[rewrite_status] = rewrite_status_counts.get(rewrite_status, 0) + 1

        reflected_subject, reflected_body, reflection = reflection_agent.critique_and_refine(
            rewritten_subject,
            rewritten_body,
            context,
        )
        reflection_mode = str(reflection.get("mode") or "unknown")
        reflection_mode_counts[reflection_mode] = reflection_mode_counts.get(reflection_mode, 0) + 1

        supervision = supervisor_agent.review(reflected_subject, reflected_body, context)
        supervisor_status = str(supervision.get("status") or "unknown")
        supervisor_status_counts[supervisor_status] = supervisor_status_counts.get(supervisor_status, 0) + 1

    contract_summary = _contract_checks()
    scenarios = len(_build_sample_contexts())

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "scenarios": scenarios,
            "routing_success_rate": round(routing_ok / scenarios, 3) if scenarios else 0.0,
            "contract_pass_rate": contract_summary["pass_rate"],
        },
        "contracts": contract_summary,
        "agent_metrics": {
            "rewrite_status_counts": rewrite_status_counts,
            "reflection_mode_counts": reflection_mode_counts,
            "supervisor_status_counts": supervisor_status_counts,
        },
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report
