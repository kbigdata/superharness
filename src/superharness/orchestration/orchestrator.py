"""Orchestrator — 공유 TaskList에 대해 에이전트를 bounded-parallel로 디스패치한다."""

from __future__ import annotations

import anyio

from superharness.agents.registry import AgentRegistry
from superharness.config import TierModelMap
from superharness.hooks.bus import HookBus
from superharness.logging import get_logger
from superharness.orchestration.task import Task, TaskList
from superharness.providers.base import Provider

log = get_logger("orchestrator")


class Orchestrator:
    """N개의 워커 코루틴이 TaskList에서 태스크를 claim해 에이전트로 실행한다."""

    def __init__(
        self,
        *,
        agents: AgentRegistry,
        provider: Provider,
        tiers: TierModelMap,
        artifacts,
        hooks: HookBus | None = None,
        max_concurrency: int = 4,
        injected_context: str = "",
    ) -> None:
        self.agents = agents
        self.provider = provider
        self.tiers = tiers
        self.artifacts = artifacts
        self.hooks = hooks
        self.max_concurrency = max(1, max_concurrency)
        self.injected_context = injected_context

    async def _worker(self, tasklist: TaskList, limiter: anyio.CapacityLimiter) -> None:
        while True:
            task = await tasklist.claim()
            if task is None:
                return
            async with limiter:
                await self._run_one(tasklist, task)

    async def _run_one(self, tasklist: TaskList, task: Task) -> None:
        try:
            agent = self.agents.get(task.domain, task.tier)
            result = await agent.run(
                task,
                provider=self.provider,
                tiers=self.tiers,
                artifacts=self.artifacts,
                hooks=self.hooks,
                injected_context=self.injected_context,
            )
            await tasklist.complete(task.id, result.artifact)
        except Exception as exc:  # noqa: BLE001 - 개별 태스크 실패를 격리
            log.warning("태스크 실패 %s: %s", task.id, exc)
            await tasklist.fail(task.id, str(exc))

    async def run(self, tasklist: TaskList) -> TaskList:
        """대기 태스크가 없을 때까지 병렬 처리. 동시성은 CapacityLimiter로 제한."""
        limiter = anyio.CapacityLimiter(self.max_concurrency)
        workers = min(self.max_concurrency, max(1, len(tasklist.pending())))
        async with anyio.create_task_group() as tg:
            for _ in range(workers):
                tg.start_soon(self._worker, tasklist, limiter)
        return tasklist
