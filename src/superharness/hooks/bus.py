"""HookBus — async pub/sub 라이프사이클 이벤트 버스 + persistent-mode STOP 가드.

persistent-mode 가드: 미검증 목표가 남아있는 동안 STOP을 차단해
Ralph/지속 모드의 비종료성을 강제한다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from superharness.hooks.events import HookOutcome, LifecycleEvent
from superharness.logging import get_logger

log = get_logger("hooks")

Handler = Callable[[dict], Awaitable[HookOutcome | None]]


class HookBus:
    def __init__(self) -> None:
        self._handlers: dict[LifecycleEvent, list[Handler]] = {}
        self.history: list[tuple[LifecycleEvent, dict]] = []

    def on(self, event: LifecycleEvent, handler: Handler) -> None:
        self._handlers.setdefault(event, []).append(handler)

    async def emit(self, event: LifecycleEvent, payload: dict | None = None) -> list[HookOutcome]:
        payload = payload or {}
        self.history.append((event, payload))
        outcomes: list[HookOutcome] = []
        for handler in self._handlers.get(event, []):
            try:
                result = await handler(payload)
            except Exception as exc:  # noqa: BLE001 - 훅 실패가 본 흐름을 막지 않게
                log.warning("훅 핸들러 실패 (%s): %s", event.value, exc)
                continue
            if result is not None:
                outcomes.append(result)
        return outcomes

    def fired(self, event: LifecycleEvent) -> int:
        """해당 이벤트가 발화된 횟수 (테스트/관측용)."""
        return sum(1 for ev, _ in self.history if ev == event)


class PersistentMode:
    """STOP 이벤트를 차단해 지속성을 강제하는 가드. is_complete가 True가 되면 차단 해제."""

    def __init__(self, bus: HookBus) -> None:
        self._complete = False
        bus.on(LifecycleEvent.STOP, self._on_stop)

    def mark_complete(self) -> None:
        self._complete = True

    def mark_incomplete(self) -> None:
        self._complete = False

    async def _on_stop(self, payload: dict) -> HookOutcome:
        if self._complete:
            return HookOutcome(block=False, reason="goal verified complete")
        return HookOutcome(block=True, reason="목표 미검증 — 지속 모드가 STOP을 차단")
