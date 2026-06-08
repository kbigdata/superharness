"""프로바이더 추상화 — 프레임워크 중립 LLM 백엔드 인터페이스.

"논리적 역할명 우선" 규율을 프로바이더 레벨에서 구현한다: 하네스 코드는 `Provider`
Protocol만 알고, 구체 백엔드(Anthropic/Mock/...)는 레지스트리로 교체된다.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Tier(StrEnum):
    """작업 난이도 티어. 모델 라우팅의 논리적 축 (LOW/MEDIUM/HIGH)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


Role = Literal["user", "assistant", "system"]
Effort = Literal["low", "medium", "high"]


class Message(BaseModel):
    """대화 메시지 한 턴."""

    role: Role
    content: str


class CompletionRequest(BaseModel):
    """프로바이더에 보내는 단일 완성 요청.

    `model`은 이미 티어→모델 해석이 끝난 구체 모델 id 문자열이다.
    """

    model: str
    messages: list[Message]
    system: str | None = None
    max_tokens: int = 4096
    effort: Effort | None = None
    thinking: bool = False


class Usage(BaseModel):
    """토큰 사용량."""

    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


class CompletionResult(BaseModel):
    """프로바이더 완성 응답."""

    text: str
    model: str
    usage: Usage = Field(default_factory=Usage)


@runtime_checkable
class Provider(Protocol):
    """LLM 백엔드 인터페이스. 구현체는 상속 없이 duck-typing으로 만족하면 된다."""

    name: str

    async def complete(self, req: CompletionRequest) -> CompletionResult: ...
