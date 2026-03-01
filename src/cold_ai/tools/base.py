from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ToolResult:
    ok: bool
    tool: str
    data: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class ToolPolicy:
    profile: str = "messaging"
    allow: tuple[str, ...] = ()
    deny: tuple[str, ...] = ()
    also_allow: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolCallRecord:
    tool: str
    args_hash: str
    timestamp_ms: int


class AgentTool(Protocol):
    name: str

    def run(self, payload: dict[str, Any]) -> ToolResult:
        ...
