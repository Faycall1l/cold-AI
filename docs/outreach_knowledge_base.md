# Outreach Knowledge Base (Static, Offline)

This project ships with a built-in static playbook used by the agent layer when external providers are unavailable or optional.

## Scope

The knowledge base currently includes:

- Channel copy rules for `email`, `whatsapp`, and `telegram`
- Follow-up cadence plans by channel
- Purpose-based messaging angles
- Specialty hooks for personalization
- Objection-handling patterns
- CTA examples
- Long-term memory pattern storage and retrieval
- Reflection self-critique pass before supervisor review

## Where It Is Used

- Tool layer: `outreach_knowledge` tool (`context` and `search` modes)
- Tool layer: `outreach_memory` tool (contextual memory retrieval)
- Draft generation: injects `knowledge_*` context keys
- Draft generation: injects `memory_patterns`
- Routing agent: angle/CTA fallback and prompt grounding
- Rewrite agent: style constraints and follow-up grounding
- Reflection agent: critique + refine loop (LLM/heuristic)
- Supervisor agent: review checklist grounding
- Research agent: specialty-hook fallback snippet when web research is empty/off

## Context Keys Added to Draft Flow

- `knowledge_principles`
- `knowledge_followup_plan`
- `knowledge_purpose_angles`
- `knowledge_specialty_hook`
- `knowledge_objection_handling`
- `knowledge_cta_examples`
- `memory_patterns`

## Memory Store

Persistent table: `outreach_memory`

Stored fields include:

- owner key
- channel, purpose, specialty
- distilled pattern text (subject/opener/CTA style)
- quality score
- source event (`draft_supervised` / `sent_success`)
- usage count and last-used timestamp

Learning events:

- high-scoring drafts after supervisor review
- successful sends in `send_due`

## Example Tool Calls

Context mode:

```json
{
  "tool": "outreach_knowledge",
  "payload": {
    "mode": "context",
    "channel": "email",
    "purpose": "lead generation",
    "specialty": "dentistry"
  }
}
```

Search mode:

```json
{
  "tool": "outreach_knowledge",
  "payload": {
    "mode": "search",
    "query": "follow-up cadence whatsapp",
    "limit": 5
  }
}
```

## Extending the KB

Edit `src/cold_ai/services/outreach_knowledge_base.py`:

- `_CHANNEL_RULES` for per-channel writing structure
- `_FOLLOWUP_CADENCE` for sequence timing
- `_PURPOSE_ANGLES` for campaign goals
- `_SPECIALTY_HOOKS` for niche personalization
- `_OBJECTION_HANDLING` for response patterns

Keep entries short and operational, so they can be inserted directly into prompts and template context.
