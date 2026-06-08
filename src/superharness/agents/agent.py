"""Agent — 도메인×티어 실행 단위. 티어→모델 해석 후 프로바이더를 호출한다."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from superharness.config import TierModelMap
from superharness.hooks.bus import HookBus
from superharness.hooks.events import LifecycleEvent
from superharness.providers.base import (
    CompletionRequest,
    Message,
    Provider,
    Tier,
    Usage,
)
from superharness.state.artifacts import ArtifactStore
from superharness.state.descriptor import ArtifactDescriptor

if TYPE_CHECKING:
    from superharness.orchestration.task import Task


class AgentSpec(BaseModel):
    """에이전트 정의: 도메인 + 티어 + 시스템 프롬프트."""

    domain: str
    tier: Tier
    name: str
    system_prompt: str


class AgentResult(BaseModel):
    agent: str
    output: str
    artifact: ArtifactDescriptor | None = None
    usage: Usage = Field(default_factory=Usage)


class Agent:
    """AgentSpec를 실행 가능한 단위로 감싼다."""

    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec

    async def run(
        self,
        task: Task,
        *,
        provider: Provider,
        tiers: TierModelMap,
        artifacts: ArtifactStore | None = None,
        hooks: HookBus | None = None,
        injected_context: str = "",
    ) -> AgentResult:
        if hooks:
            await hooks.emit(
                LifecycleEvent.SUBAGENT_START,
                {"agent": self.spec.name, "task": task.id},
            )

        system = self.spec.system_prompt
        if injected_context:
            system = f"{system}\n\n{injected_context}"

        req = CompletionRequest(
            model=tiers.resolve(self.spec.tier),
            system=system,
            messages=[Message(role="user", content=task.description)],
            thinking=self.spec.tier == Tier.HIGH,
            effort="high" if self.spec.tier == Tier.HIGH else None,
        )
        result = await provider.complete(req)

        descriptor: ArtifactDescriptor | None = None
        if artifacts is not None:
            kind = "result" if self.spec.domain != "planner" else "plan"
            descriptor = artifacts.write(kind, result.text, producer=self.spec.name)

        if hooks:
            await hooks.emit(
                LifecycleEvent.SUBAGENT_STOP,
                {"agent": self.spec.name, "task": task.id},
            )

        return AgentResult(
            agent=self.spec.name,
            output=result.text,
            artifact=descriptor,
            usage=result.usage,
        )
