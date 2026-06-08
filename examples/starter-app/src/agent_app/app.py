"""앱 코어 — 슈퍼하네스 구성 요소를 조립한다.

여기서 보여주는 재사용 패턴:
  1) 커스텀 스킬 디렉토리를 SkillRegistry에 로드 (키워드→스킬 활성화 확장)
  2) AgentRegistry에 커스텀 에이전트(reviewer) 추가 (도메인×티어 매트릭스 확장)
  3) TeamPipeline로 plan→exec→verify→fix 실행 (오케스트레이션 엔진 재사용)
  4) 커스텀 에이전트 단일 디스패치
모두 기본 mock 프로바이더로 오프라인 동작하며, SUPERHARNESS_PROVIDER=anthropic 로 실 Claude 전환.
"""

from __future__ import annotations

from pathlib import Path

from superharness.agents import Agent, AgentRegistry, AgentResult, AgentSpec
from superharness.config import Settings, load_settings
from superharness.hooks import HookBus, PersistentMode
from superharness.orchestration import PipelineResult, Task, TeamPipeline
from superharness.providers import get_provider
from superharness.providers.base import Provider, Tier
from superharness.skills import Activation, SkillRegistry
from superharness.state import ArtifactStore, StateLayout, StateStore

# 앱이 패키징하는 커스텀 스킬 디렉토리
_SKILLS_DIR = Path(__file__).parent / "skills"

# 한 번에 배선되는 슈퍼하네스 구성 요소 묶음
Wiring = tuple[StateLayout, ArtifactStore, StateStore, HookBus, PersistentMode, Provider]


def build_skills() -> SkillRegistry:
    """builtin + 앱 전용 스킬을 함께 로드한다."""
    return SkillRegistry.load(extra_dirs=[_SKILLS_DIR])


def build_agents() -> AgentRegistry:
    """기본 매트릭스에 커스텀 'reviewer' 에이전트를 추가한다."""
    specs = AgentRegistry.default().specs + [
        AgentSpec(
            domain="reviewer",
            tier=Tier.MEDIUM,
            name="reviewer",
            system_prompt="당신은 코드 리뷰어입니다. 버그와 간결화 개선점을 찾아 보고하세요.",
        )
    ]
    return AgentRegistry(specs)


def _wire(settings: Settings) -> Wiring:
    layout = StateLayout(settings.state_dir).init()
    artifacts = ArtifactStore(layout)
    store = StateStore(layout)
    hooks = HookBus()
    persistent = PersistentMode(hooks)
    provider = get_provider(settings.provider)
    return layout, artifacts, store, hooks, persistent, provider


async def run_goal(goal: str) -> tuple[Activation, PipelineResult]:
    """키워드 활성화 → Team 파이프라인 실행. 활성화 결과와 파이프라인 결과를 돌려준다."""
    settings = load_settings()
    skills = build_skills()
    activation = skills.activate(goal)

    _, artifacts, store, hooks, persistent, provider = _wire(settings)
    store.create_session("agent-app")

    pipeline = TeamPipeline(
        agents=build_agents(),
        provider=provider,
        settings=settings,
        artifacts=artifacts,
        hooks=hooks,
        persistent=persistent,
        injected_context=activation.injected_context,
    )
    result = await pipeline.run(goal)
    store.merge_memory({"last_goal": goal, "verified": result.verified})
    return activation, result


async def run_reviewer(text: str) -> AgentResult:
    """커스텀 'reviewer' 에이전트를 단일 디스패치한다."""
    settings = load_settings()
    _, artifacts, _, hooks, _, provider = _wire(settings)
    agent: Agent = build_agents().get_by_name("reviewer")
    task = Task(id="review", domain="reviewer", tier=Tier.MEDIUM, description=text)
    return await agent.run(
        task, provider=provider, tiers=settings.tiers, artifacts=artifacts, hooks=hooks
    )
