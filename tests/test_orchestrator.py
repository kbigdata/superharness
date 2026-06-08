from __future__ import annotations

from superharness.config import TierModelMap
from superharness.orchestration.orchestrator import Orchestrator
from superharness.orchestration.task import Task, TaskList, TaskStatus
from superharness.providers.base import CompletionRequest, CompletionResult, Tier


def _tasks(n: int) -> list[Task]:
    return [
        Task(id=f"t{i}", domain="executor", tier=Tier.MEDIUM, description=f"task {i}")
        for i in range(n)
    ]


class FailingProvider:
    """항상 예외를 던지는 프로바이더 — 실패 경로 검증용."""

    name = "failing"

    async def complete(self, req: CompletionRequest) -> CompletionResult:
        raise RuntimeError("boom")


async def test_all_tasks_reach_done(agents, mock_provider, artifacts):
    tasklist = TaskList(_tasks(8))
    orch = Orchestrator(
        agents=agents,
        provider=mock_provider,
        tiers=TierModelMap(),
        artifacts=artifacts,
        max_concurrency=4,
    )
    await orch.run(tasklist)
    assert tasklist.all_done()
    assert all(t.status == TaskStatus.DONE for t in tasklist.tasks)


async def test_each_task_claimed_once(agents, mock_provider, artifacts):
    tasklist = TaskList(_tasks(10))
    orch = Orchestrator(
        agents=agents,
        provider=mock_provider,
        tiers=TierModelMap(),
        artifacts=artifacts,
        max_concurrency=4,
    )
    await orch.run(tasklist)
    # 각 태스크가 정확히 한 번 실행되어 mock 호출 수 == 태스크 수
    assert len(mock_provider.calls) == 10


async def test_tier_routing_resolves_model(agents, mock_provider, artifacts):
    tasklist = TaskList([Task(id="x", domain="executor", tier=Tier.HIGH, description="go")])
    orch = Orchestrator(
        agents=agents,
        provider=mock_provider,
        tiers=TierModelMap(),
        artifacts=artifacts,
        max_concurrency=2,
    )
    await orch.run(tasklist)
    # HIGH 티어 → opus 모델이 요청에 실렸는지 (라우팅 검증)
    assert mock_provider.calls[0].model == "claude-opus-4-8"


async def test_failure_path_marks_task_failed(agents, artifacts):
    tasklist = TaskList([Task(id="x", domain="executor", tier=Tier.MEDIUM, description="go")])
    orch = Orchestrator(
        agents=agents,
        provider=FailingProvider(),
        tiers=TierModelMap(),
        artifacts=artifacts,
        max_concurrency=2,
    )
    await orch.run(tasklist)
    # 개별 태스크 실패가 격리되어 FAILED로 표시되고 에러가 기록된다
    assert not tasklist.all_done()
    assert tasklist.tasks[0].status == TaskStatus.FAILED
    assert tasklist.tasks[0].error
