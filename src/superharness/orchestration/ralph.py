"""RalphLoop — 지속/검증 루프. complete까지 verify→fix를 반복한다.

제네릭 verify/fix 콜러블을 받으므로 Team fix-loop와 standalone /ralph 양쪽을 구동한다.
persistent-mode STOP 가드와 연동해 부분 완료 종료를 막는다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from superharness.hooks.bus import PersistentMode
from superharness.hooks.events import LifecycleEvent
from superharness.logging import get_logger

log = get_logger("ralph")


class VerifyReport(BaseModel):
    complete: bool
    detail: str = ""


class RalphResult(BaseModel):
    complete: bool
    iterations: int
    detail: str = ""


VerifyFn = Callable[[], Awaitable[VerifyReport]]
FixFn = Callable[[VerifyReport], Awaitable[None]]


class RalphLoop:
    def __init__(
        self,
        verify: VerifyFn,
        fix: FixFn,
        *,
        max_iterations: int = 10,
        persistent: PersistentMode | None = None,
        hooks=None,
    ) -> None:
        self._verify = verify
        self._fix = fix
        self._max = max(1, max_iterations)
        self._persistent = persistent
        self._hooks = hooks

    async def run(self) -> RalphResult:
        last = ""
        for i in range(1, self._max + 1):
            report = await self._verify()
            last = report.detail
            if report.complete:
                if self._persistent:
                    self._persistent.mark_complete()
                if self._hooks:
                    await self._hooks.emit(LifecycleEvent.STOP, {"complete": True})
                log.info("Ralph 완료 (반복 %d): %s", i, report.detail)
                return RalphResult(complete=True, iterations=i, detail=report.detail)

            # 미완료 — STOP 차단 유지 후 fix
            if self._persistent:
                self._persistent.mark_incomplete()
            if self._hooks:
                await self._hooks.emit(LifecycleEvent.STOP, {"complete": False})
            log.info("Ralph 미완료 (반복 %d): %s — fix 진행", i, report.detail)
            await self._fix(report)

        return RalphResult(complete=False, iterations=self._max, detail=last)
