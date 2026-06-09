from __future__ import annotations

from superharness.hooks.bus import HookBus
from superharness.hooks.events import LifecycleEvent
from superharness.state.memory_recorder import MemoryRecorder
from superharness.state.store import StateStore


async def test_subagent_stop_is_recorded(store: StateStore):
    hooks = HookBus()
    MemoryRecorder(hooks, store)

    await hooks.emit(LifecycleEvent.SUBAGENT_START, {"agent": "executor", "task": "t1"})
    await hooks.emit(LifecycleEvent.SUBAGENT_STOP, {"agent": "executor", "task": "t1"})

    events = store.read_memory().get("events", [])
    assert len(events) == 1
    assert events[0]["event"] == "subagent_stop"
    assert events[0]["agent"] == "executor"
    assert "at" in events[0]  # 타임스탬프 자동 부착


async def test_session_end_records_event_and_flat_fact(store: StateStore):
    hooks = HookBus()
    MemoryRecorder(hooks, store)

    await hooks.emit(LifecycleEvent.SESSION_END, {"goal": "build parser"})

    memory = store.read_memory()
    assert memory["last_session_goal"] == "build parser"
    assert any(e["event"] == "session_end" for e in memory["events"])


async def test_pre_compact_flush_point(store: StateStore):
    hooks = HookBus()
    MemoryRecorder(hooks, store)

    await hooks.emit(LifecycleEvent.PRE_COMPACT, {"reason": "context full"})

    events = store.read_memory()["events"]
    assert events[0]["event"] == "pre_compact"
    assert events[0]["reason"] == "context full"


async def test_recorder_accumulates_across_events(store: StateStore):
    hooks = HookBus()
    MemoryRecorder(hooks, store)

    for i in range(3):
        await hooks.emit(LifecycleEvent.SUBAGENT_STOP, {"agent": "executor", "task": f"t{i}"})

    assert len(store.read_memory()["events"]) == 3
