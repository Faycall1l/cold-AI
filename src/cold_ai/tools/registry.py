from __future__ import annotations

import hashlib
import json
import time
from collections import deque
from typing import Any

from ..config import settings
from .base import AgentTool, ToolCallRecord, ToolPolicy, ToolResult

TOOL_NAME_ALIASES = {
    "bash": "exec",
    "apply-patch": "apply_patch",
}

TOOL_PROFILES = {
    "minimal": {"web_search"},
    "messaging": {
        "email",
        "whatsapp",
        "telegram",
        "web_search",
        "outreach_knowledge",
        "outreach_memory",
    },
    "full": {"*"},
}


def normalize_tool_name(name: str) -> str:
    return TOOL_NAME_ALIASES.get(name.strip().lower(), name.strip().lower())


def _hash_tool_call(tool_name: str, payload: dict[str, Any]) -> str:
    try:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    except TypeError:
        serialized = str(payload)
    raw = f"{tool_name}:{serialized}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _resolve_policy_allowlist(policy: ToolPolicy) -> set[str]:
    profile = policy.profile if policy.profile in TOOL_PROFILES else "messaging"
    base_allow = set(TOOL_PROFILES.get(profile, set()))
    base_allow.update(normalize_tool_name(name) for name in policy.allow)
    base_allow.update(normalize_tool_name(name) for name in policy.also_allow)
    return base_allow


class ToolRegistry:
    def __init__(self, policy: ToolPolicy | None = None) -> None:
        self._tools: dict[str, AgentTool] = {}
        self._policy = policy or ToolPolicy(
            profile=settings.tool_profile,
            allow=settings.tools_allow,
            deny=settings.tools_deny,
        )
        self._history: deque[ToolCallRecord] = deque(maxlen=max(10, settings.tool_loop_history_size))

    def register(self, tool: AgentTool) -> None:
        self._tools[normalize_tool_name(tool.name)] = tool

    def set_policy(self, policy: ToolPolicy) -> None:
        self._policy = policy

    def get_policy(self) -> ToolPolicy:
        return self._policy

    def _is_allowed(self, tool_name: str) -> bool:
        normalized = normalize_tool_name(tool_name)
        allowlist = _resolve_policy_allowlist(self._policy)
        denylist = {normalize_tool_name(name) for name in self._policy.deny}
        if normalized in denylist:
            return False
        return "*" in allowlist or normalized in allowlist

    def _is_loop_blocked(self, tool_name: str, payload: dict[str, Any]) -> bool:
        if not settings.tool_loop_detection_enabled:
            return False

        current_hash = _hash_tool_call(tool_name, payload)
        now_ms = int(time.time() * 1000)
        self._history.append(ToolCallRecord(tool=tool_name, args_hash=current_hash, timestamp_ms=now_ms))

        repeat_count = sum(
            1
            for item in self._history
            if item.tool == tool_name and item.args_hash == current_hash
        )
        return repeat_count >= max(2, settings.tool_loop_critical_threshold)

    def available(self) -> list[str]:
        return sorted([name for name in self._tools if self._is_allowed(name)])

    def run(self, tool_name: str, payload: dict[str, Any]) -> ToolResult:
        normalized = normalize_tool_name(tool_name)
        tool = self._tools.get(normalized)
        if not tool:
            return ToolResult(ok=False, tool=normalized, data={}, error=f"Unknown tool: {normalized}")

        if not self._is_allowed(normalized):
            return ToolResult(
                ok=False,
                tool=normalized,
                data={"status": "blocked", "reason": "policy_denied"},
                error=f"Tool blocked by policy: {normalized}",
            )

        if self._is_loop_blocked(normalized, payload):
            return ToolResult(
                ok=False,
                tool=normalized,
                data={"status": "blocked", "reason": "loop_detected"},
                error=f"Loop protection blocked repeated call to {normalized}",
            )

        return tool.run(payload)
