"""E2E 수직 슬라이스 — 오프라인(mock). detect→inject→pipeline→ralph→artifacts."""

from __future__ import annotations

from superharness.agents.registry import AgentRegistry
from superharness.hooks.bus import HookBus, PersistentMode
from superharness.hooks.events import LifecycleEvent
from superharness.orchestration.pipeline import TeamPipeline
from superharness.providers.base import CompletionRequest, CompletionResult
from superharness.skills.registry import SkillRegistry
from superharness.state.artifacts import ArtifactStore
from superharness.state.store import StateStore


class QAStatefulProvider:
    """qa-tester는 첫 검증에서 FAIL, 이후 PASS를 반환하는 결정적 프로바이더."""

    name = "qa-stateful"

    def __init__(self) -> None:
        self.calls: list[CompletionRequest] = []
        self._qa = 0

    async def complete(self, req: CompletionRequest) -> CompletionResult:
        self.calls.append(req)
        if req.system and "QA 테스터" in req.system:
            self._qa += 1
            text = "FAIL: tests do not pass yet" if self._qa == 1 else "PASS: all tests pass"
        else:
            last = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
            text = f"[mock:{req.model}] {last}"
        return CompletionResult(text=text, model=req.model)


async def test_e2e_offline(layout, settings):
    prompt = "ultrawork: build a CSV parser, don't stop until tests pass"

    # 1. detect → inject
    reg = SkillRegistry.load()
    activation = reg.activate(prompt)
    assert {"ultrawork", "ralph"} <= set(activation.skills)
    assert activation.mode == "ralph"

    # 2. 파이프라인 구성
    artifacts = ArtifactStore(layout)
    store = StateStore(layout)
    store.create_session("e2e")
    hooks = HookBus()
    persistent = PersistentMode(hooks)
    provider = QAStatefulProvider()

    pipeline = TeamPipeline(
        agents=AgentRegistry.default(),
        provider=provider,
        settings=settings,
        artifacts=artifacts,
        hooks=hooks,
        persistent=persistent,
        injected_context=activation.injected_context,
    )

    # 3. 실행: plan → exec → verify(FAIL) → fix → verify(PASS)
    result = await pipeline.run(prompt)

    # 4. 검증
    assert result.verified is True
    assert result.iterations == 2  # FAIL 1회 후 PASS
    assert result.plan is not None
    assert artifacts.read(result.plan)  # 유효 해시로 읽힘
    assert len(result.results) >= 1

    # 라이프사이클 이벤트 발화
    assert hooks.fired(LifecycleEvent.SESSION_START) == 1
    assert hooks.fired(LifecycleEvent.SESSION_END) == 1
    assert hooks.fired(LifecycleEvent.SUBAGENT_START) >= 1
    assert hooks.fired(LifecycleEvent.SUBAGENT_STOP) >= 1
    assert hooks.fired(LifecycleEvent.STOP) >= 1

    # project-memory 갱신
    store.merge_memory({"last_goal": prompt, "verified": result.verified})
    assert store.read_memory()["verified"] is True
