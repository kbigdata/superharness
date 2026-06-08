"""TeamPipeline — plan → exec → verify → fix(loop). Team 파이프라인의 코어.

plan(planner) → 태스크 생성 → exec(executor 병렬) → verify(qa-tester) → 실패 시 RalphLoop로 fix.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from superharness.agents.registry import AgentRegistry
from superharness.config import Settings
from superharness.hooks.bus import HookBus, PersistentMode
from superharness.hooks.events import LifecycleEvent
from superharness.logging import get_logger
from superharness.orchestration.orchestrator import Orchestrator
from superharness.orchestration.ralph import RalphLoop, VerifyReport
from superharness.orchestration.task import Task, TaskList
from superharness.providers.base import Provider, Tier
from superharness.state.artifacts import ArtifactStore
from superharness.state.descriptor import ArtifactDescriptor

log = get_logger("pipeline")


class PipelineResult(BaseModel):
    goal: str
    plan: ArtifactDescriptor | None = None
    results: list[ArtifactDescriptor] = Field(default_factory=list)
    verified: bool = False
    iterations: int = 0
    detail: str = ""


def _derive_tasks(plan_text: str, goal: str) -> list[Task]:
    """플랜 텍스트에서 실행 태스크를 도출한다. '- ' 라인을 서브태스크로, 없으면 단일 태스크."""
    lines = [ln.strip()[1:].strip() for ln in plan_text.splitlines() if ln.strip().startswith("-")]
    items = lines or [goal]
    return [
        Task(id=f"exec-{i}", domain="executor", tier=Tier.MEDIUM, description=desc)
        for i, desc in enumerate(items)
    ]


class TeamPipeline:
    def __init__(
        self,
        *,
        agents: AgentRegistry,
        provider: Provider,
        settings: Settings,
        artifacts: ArtifactStore,
        hooks: HookBus | None = None,
        persistent: PersistentMode | None = None,
        injected_context: str = "",
    ) -> None:
        self.agents = agents
        self.provider = provider
        self.settings = settings
        self.artifacts = artifacts
        self.hooks = hooks or HookBus()
        self.persistent = persistent
        self.injected_context = injected_context

    def _orchestrator(self) -> Orchestrator:
        return Orchestrator(
            agents=self.agents,
            provider=self.provider,
            tiers=self.settings.tiers,
            artifacts=self.artifacts,
            hooks=self.hooks,
            max_concurrency=self.settings.max_concurrency,
            injected_context=self.injected_context,
        )

    async def run(self, goal: str) -> PipelineResult:
        await self.hooks.emit(LifecycleEvent.SESSION_START, {"goal": goal})

        # 1. plan
        plan_task = Task(id="plan", domain="planner", tier=Tier.HIGH, description=goal)
        planner = self.agents.get("planner", Tier.HIGH)
        plan_res = await planner.run(
            plan_task,
            provider=self.provider,
            tiers=self.settings.tiers,
            artifacts=self.artifacts,
            hooks=self.hooks,
            injected_context=self.injected_context,
        )

        # 2. 태스크 생성 + exec
        tasklist = TaskList(_derive_tasks(plan_res.output, goal))
        orch = self._orchestrator()

        async def _verify() -> VerifyReport:
            outputs = []
            for t in tasklist.tasks:
                if t.result is not None:
                    outputs.append(self.artifacts.read(t.result))
            qa = self.agents.get("qa-tester", Tier.MEDIUM)
            qa_task = Task(
                id="verify",
                domain="qa-tester",
                tier=Tier.MEDIUM,
                description=f"목표: {goal}\n산출물:\n" + "\n---\n".join(outputs),
            )
            qa_res = await qa.run(
                qa_task,
                provider=self.provider,
                tiers=self.settings.tiers,
                artifacts=None,
                hooks=self.hooks,
            )
            complete = "FAIL" not in qa_res.output.upper()
            return VerifyReport(complete=complete, detail=qa_res.output)

        async def _fix(_: VerifyReport) -> None:
            # verify는 파이프라인 단위 판정이므로 fix 시 모든 exec 태스크를 재실행한다.
            for t in tasklist.tasks:
                await tasklist.reopen(t.id)
            await orch.run(tasklist)

        # 첫 exec
        await orch.run(tasklist)

        # 3+4. verify → fix loop (Ralph)
        ralph = RalphLoop(
            _verify,
            _fix,
            max_iterations=self.settings.max_iterations,
            persistent=self.persistent,
            hooks=self.hooks,
        )
        ralph_result = await ralph.run()

        results = [t.result for t in tasklist.tasks if t.result is not None]
        await self.hooks.emit(LifecycleEvent.SESSION_END, {"goal": goal})

        return PipelineResult(
            goal=goal,
            plan=plan_res.artifact,
            results=results,
            verified=ralph_result.complete,
            iterations=ralph_result.iterations,
            detail=ralph_result.detail,
        )
