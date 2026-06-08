from __future__ import annotations

from superharness.hooks.bus import HookBus, PersistentMode
from superharness.hooks.events import LifecycleEvent
from superharness.orchestration.ralph import RalphLoop, VerifyReport


async def test_verify_incomplete_then_complete():
    state = {"verifies": 0, "fixes": 0}

    async def verify() -> VerifyReport:
        state["verifies"] += 1
        return VerifyReport(complete=state["verifies"] >= 3, detail=f"v{state['verifies']}")

    async def fix(_: VerifyReport) -> None:
        state["fixes"] += 1

    result = await RalphLoop(verify, fix, max_iterations=10).run()
    assert result.complete
    assert result.iterations == 3
    assert state["fixes"] == 2


async def test_persistent_mode_blocks_stop_until_complete():
    hooks = HookBus()
    persistent = PersistentMode(hooks)
    state = {"n": 0}

    async def verify() -> VerifyReport:
        state["n"] += 1
        return VerifyReport(complete=state["n"] >= 2)

    async def fix(_: VerifyReport) -> None:
        pass

    # 첫 STOP(미완료)은 차단, 완료 후 STOP은 통과
    await RalphLoop(verify, fix, max_iterations=5, persistent=persistent, hooks=hooks).run()
    stop_events = [p for ev, p in hooks.history if ev == LifecycleEvent.STOP]
    assert stop_events[0]["complete"] is False
    assert stop_events[-1]["complete"] is True


async def test_max_iterations_cap():
    async def verify() -> VerifyReport:
        return VerifyReport(complete=False, detail="never")

    async def fix(_: VerifyReport) -> None:
        pass

    result = await RalphLoop(verify, fix, max_iterations=4).run()
    assert not result.complete
    assert result.iterations == 4
