from __future__ import annotations

from dataclasses import dataclass

from ..config import settings


@dataclass(frozen=True)
class AgentLLMConfig:
    provider: str
    base_url: str
    api_key: str | None
    models: tuple[str, ...]
    enable_web_research: bool
    enable_llm_rewrite: bool
    prompt_search: str
    prompt_routing: str
    prompt_supervisor: str
    prompt_rewrite: str


DEFAULT_PROMPT_SEARCH = (
    "You are a search agent for B2B medical outreach. Create one concise, high-signal web query for this lead."
)
DEFAULT_PROMPT_ROUTING = (
    "You are a routing agent. Decide best messaging angle and channel strategy for this lead and campaign."
)
DEFAULT_PROMPT_SUPERVISOR = (
    "You are a supervisor agent. Evaluate if the outreach draft is safe, credible, and personalized."
)
DEFAULT_PROMPT_REWRITE = (
    "You are a rewrite agent. Rewrite drafts to be concise, human, and trustworthy."
)


PROVIDER_PRESETS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ("gpt-4o-mini", "gpt-4.1-mini"),
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "models": ("openai/gpt-4.1-mini", "anthropic/claude-3.5-sonnet"),
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": ("llama-3.3-70b-versatile",),
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "models": ("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",),
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "models": ("llama3.1:8b",),
    },
    "vllm": {
        "base_url": "http://127.0.0.1:8000/v1",
        "models": ("my-vllm-model",),
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "models": ("claude-3-5-sonnet-latest",),
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com",
        "models": ("gemini-1.5-flash",),
    },
}


def list_provider_options() -> list[dict[str, str]]:
    return [
        {"id": provider, "label": provider.title().replace("Vllm", "vLLM")}
        for provider in PROVIDER_PRESETS.keys()
    ]


def resolve_agent_llm_config(agent_settings: dict | None = None) -> AgentLLMConfig:
    row = agent_settings or {}
    provider = str(row.get("llm_provider") or "openai").strip().lower()
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["openai"])

    row_models = row.get("llm_models") or []
    models = tuple(str(m).strip() for m in row_models if str(m).strip()) or preset["models"] or settings.llm_models

    return AgentLLMConfig(
        provider=provider,
        base_url=str(row.get("llm_base_url") or preset["base_url"] or settings.llm_base_url),
        api_key=(row.get("llm_api_key") or settings.llm_api_key),
        models=models,
        enable_web_research=bool(
            row.get("enable_web_research")
            if row.get("enable_web_research") is not None
            else settings.enable_web_research
        ),
        enable_llm_rewrite=bool(
            row.get("enable_llm_rewrite")
            if row.get("enable_llm_rewrite") is not None
            else settings.enable_llm_rewrite
        ),
        prompt_search=str(row.get("prompt_search") or DEFAULT_PROMPT_SEARCH),
        prompt_routing=str(row.get("prompt_routing") or DEFAULT_PROMPT_ROUTING),
        prompt_supervisor=str(row.get("prompt_supervisor") or DEFAULT_PROMPT_SUPERVISOR),
        prompt_rewrite=str(row.get("prompt_rewrite") or DEFAULT_PROMPT_REWRITE),
    )
