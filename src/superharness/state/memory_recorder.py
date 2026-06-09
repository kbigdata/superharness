"""MemoryRecorder — 라이프사이클 이벤트를 구독해 project-memory에 자동 적립한다.

PersistentMode가 STOP에 핸들러를 거는 것과 동일한 패턴(생성 시 HookBus.on 등록).
"수동 1회 호출"이던 메모리를 OMC식 passive(상시 자동) 적립으로 바꾸는 인프로세스 구현.
"""

from __future__ import annotations

from superharness.hooks.bus import HookBus
from superharness.hooks.events import LifecycleEvent
from superharness.state.store import StateStore


class MemoryRecorder:
    """세션/서브에이전트 라이프사이클을 구독해 project-memory.json에 이벤트를 누적한다."""

    def __init__(self, bus: HookBus, store: StateStore) -> None:
        self._store = store
        bus.on(LifecycleEvent.SUBAGENT_STOP, self._on_subagent_stop)
        bus.on(LifecycleEvent.SESSION_END, self._on_session_end)
        bus.on(LifecycleEvent.PRE_COMPACT, self._on_pre_compact)

    async def _on_subagent_stop(self, payload: dict) -> None:
        # 어떤 에이전트가 어떤 태스크를 끝냈는지 활동 로그로 누적
        self._store.append_memory_event(
            {"event": "subagent_stop", "agent": payload.get("agent"), "task": payload.get("task")}
        )

    async def _on_session_end(self, payload: dict) -> None:
        # 세션 종료 시 마지막 목표를 평면 사실로도 기록 (빠른 회상용)
        goal = payload.get("goal")
        if goal is not None:
            self._store.merge_memory({"last_session_goal": goal})
        self._store.append_memory_event({"event": "session_end", "goal": goal})

    async def _on_pre_compact(self, payload: dict) -> None:
        # 컨텍스트 압축 직전 flush 지점 — 인프로세스엔 실제 compaction이 없으므로
        # 통합 지점만 제공한다(추후 외부 하네스가 emit하면 자동 보존).
        self._store.append_memory_event({"event": "pre_compact", **payload})
