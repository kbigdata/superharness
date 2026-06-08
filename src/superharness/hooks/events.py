"""라이프사이클 이벤트 정의."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class LifecycleEvent(StrEnum):
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    STOP = "Stop"


class HookOutcome(BaseModel):
    """훅 핸들러의 반환. block=True면 해당 이벤트(특히 STOP)를 차단한다."""

    block: bool = False
    reason: str = ""
    data: dict = Field(default_factory=dict)
