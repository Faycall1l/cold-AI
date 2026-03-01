from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KBRule:
    title: str
    details: str


_CHANNEL_RULES = {
    "email": [
        KBRule("Subject line", "Use 4-8 words, specific outcome, no hype or urgency bait."),
        KBRule("Body structure", "1) personalized opener 2) value in one sentence 3) clear low-friction CTA."),
        KBRule("Length", "Target 80-140 words for first touch."),
    ],
    "whatsapp": [
        KBRule("Opening", "Ask permission quickly and reference context in the first sentence."),
        KBRule("Length", "Keep first message under 60 words; one ask only."),
        KBRule("Tone", "Conversational and respectful; avoid formal bulk-message style."),
    ],
    "telegram": [
        KBRule("Clarity", "Lead with why this message matters to them now."),
        KBRule("Formatting", "Use short paragraphs and one bullet max for readability."),
        KBRule("CTA", "Offer a simple yes/no next step."),
    ],
}

_FOLLOWUP_CADENCE = {
    "email": [
        "Day 0: personalized first touch",
        "Day 3: follow-up with one concrete benefit",
        "Day 7: add lightweight proof point or case snippet",
        "Day 12: short close-out with opt-out",
    ],
    "whatsapp": [
        "Day 0: permission-based intro",
        "Day 2: quick reminder with one-line value",
        "Day 5: ask a binary question to reduce friction",
    ],
    "telegram": [
        "Day 0: contextual opener",
        "Day 3: concise follow-up with one resource",
        "Day 7: close-out note with easy reply prompt",
    ],
}

_PURPOSE_ANGLES = {
    "lead generation": [
        "Focus on appointment volume and no-show reduction.",
        "Position the offer as a small pilot, not a full commitment.",
    ],
    "phone outreach": [
        "Use short scripts that request permission before pitching.",
        "Offer two time-slot options to simplify replies.",
    ],
    "partnership": [
        "Emphasize mutual value and audience fit.",
        "Propose one concrete collaboration experiment.",
    ],
}

_SPECIALTY_HOOKS = {
    "dent": "You can reference preventive care reminders and retention for recurring visits.",
    "cardio": "Highlight adherence follow-ups and continuity of care communication.",
    "pedi": "Mention family-friendly communication and appointment reminder consistency.",
    "diab": "Frame value around monitoring cadence and patient education touchpoints.",
    "nutrition": "Use behavior-change nudges and periodic check-in messaging as examples.",
}

_OBJECTION_HANDLING = [
    "No time: propose a 10-15 minute intro with two scheduling options.",
    "Already using another tool: ask what is missing and offer a focused pilot.",
    "Not interested: thank them, leave one useful resource, and pause outreach respectfully.",
]


def _match_specialty_hook(specialty: str) -> str:
    lower = (specialty or "").lower()
    for key, hook in _SPECIALTY_HOOKS.items():
        if key in lower:
            return hook
    return "Anchor personalization on patient experience, operational efficiency, and trust."


def _match_purpose_angles(purpose: str) -> list[str]:
    lower = (purpose or "").strip().lower()
    if not lower:
        return []

    for key, angles in _PURPOSE_ANGLES.items():
        if key in lower:
            return angles

    return [
        "Keep the message focused on one measurable outcome.",
        "Suggest a low-risk next step with minimal setup.",
    ]


def build_outreach_knowledge_context(
    *,
    channel: str,
    purpose: str,
    specialty: str,
) -> dict[str, Any]:
    normalized_channel = (channel or "email").strip().lower() or "email"
    channel_rules = _CHANNEL_RULES.get(normalized_channel, _CHANNEL_RULES["email"])
    followup_plan = _FOLLOWUP_CADENCE.get(normalized_channel, _FOLLOWUP_CADENCE["email"])

    purpose_angles = _match_purpose_angles(purpose)
    specialty_hook = _match_specialty_hook(specialty)

    return {
        "channel": normalized_channel,
        "principles": [rule.details for rule in channel_rules],
        "principles_named": [{"title": rule.title, "details": rule.details} for rule in channel_rules],
        "followup_plan": followup_plan,
        "purpose_angles": purpose_angles,
        "specialty_hook": specialty_hook,
        "objection_handling": list(_OBJECTION_HANDLING),
        "cta_examples": [
            "Would you be open to a short 15-minute intro next week?",
            "If useful, I can share a 3-step outline tailored to your practice.",
            "Would Tuesday 11:00 or Wednesday 14:00 work better for a quick call?",
        ],
    }


def search_outreach_knowledge(query: str, limit: int = 5) -> list[dict[str, str]]:
    q = (query or "").strip().lower()
    if not q:
        return []

    corpus: list[tuple[str, str]] = []

    for channel, rules in _CHANNEL_RULES.items():
        for rule in rules:
            corpus.append((f"{channel}: {rule.title}", rule.details))

    for channel, steps in _FOLLOWUP_CADENCE.items():
        for step in steps:
            corpus.append((f"{channel}: follow-up", step))

    for purpose, angles in _PURPOSE_ANGLES.items():
        for angle in angles:
            corpus.append((f"purpose: {purpose}", angle))

    for specialty, hook in _SPECIALTY_HOOKS.items():
        corpus.append((f"specialty: {specialty}", hook))

    for item in _OBJECTION_HANDLING:
        corpus.append(("objection handling", item))

    scored: list[tuple[int, str, str]] = []
    query_terms = [term for term in q.split() if len(term) > 2]

    for topic, content in corpus:
        text = f"{topic} {content}".lower()
        score = 0
        for term in query_terms:
            if term in text:
                score += 1
        if q in text:
            score += 2
        if score > 0:
            scored.append((score, topic, content))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {"topic": topic, "content": content}
        for _, topic, content in scored[: max(1, min(limit, 10))]
    ]
