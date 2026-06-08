"""Task + TaskList — 공유 컨트롤플레인 태스크 큐 (async-safe claim/complete/fail)."""

from __future__ import annotations

import asyncio
from enum import StrEnum

from pydantic import BaseModel

from superharness.providers.base import Tier
from superharness.state.descriptor import ArtifactDescriptor


class TaskStatus(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    DONE = "done"
    FAILED = "failed"


class Task(BaseModel):
    id: str
    domain: str
    tier: Tier
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: ArtifactDescriptor | None = None
    error: str | None = None


class TaskList:
    """공유 태스크 리스트. claim/complete/fail은 단일 Lock으로 원자적."""

    def __init__(self, tasks: list[Task] | None = None) -> None:
        self._tasks: dict[str, Task] = {t.id: t for t in (tasks or [])}
        self._lock = asyncio.Lock()

    def add(self, task: Task) -> None:
        self._tasks[task.id] = task

    @property
    def tasks(self) -> list[Task]:
        return list(self._tasks.values())

    def pending(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]

    async def claim(self) -> Task | None:
        """대기 중인 태스크 하나를 원자적으로 CLAIMED 표시하고 반환."""
        async with self._lock:
            for t in self._tasks.values():
                if t.status == TaskStatus.PENDING:
                    t.status = TaskStatus.CLAIMED
                    return t
            return None

    async def complete(self, task_id: str, result: ArtifactDescriptor | None = None) -> None:
        async with self._lock:
            t = self._tasks[task_id]
            t.status = TaskStatus.DONE
            t.result = result

    async def fail(self, task_id: str, error: str) -> None:
        async with self._lock:
            t = self._tasks[task_id]
            t.status = TaskStatus.FAILED
            t.error = error

    async def reopen(self, task_id: str) -> None:
        """실패/완료 태스크를 다시 PENDING으로 (fix 루프용)."""
        async with self._lock:
            t = self._tasks[task_id]
            t.status = TaskStatus.PENDING
            t.error = None

    def all_done(self) -> bool:
        return all(t.status == TaskStatus.DONE for t in self._tasks.values())
