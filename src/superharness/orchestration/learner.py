"""SkillLearner — 검증된 세션에서 재사용 스킬을 추출(제안)한다.

Hermes식 자동 스킬 생성의 안전한 형태:
  Goal-Driven 게이트(검증 통과 세션만) → learner(HIGH) 추출 → SkillWriter 게이트 후 격리.
자동 활성화하지 않으며, 사람이 promote해야 적용된다.
"""

from __future__ import annotations

from superharness.agents.registry import AgentRegistry
from superharness.config import TierModelMap
from superharness.hooks.bus import HookBus
from superharness.orchestration.task import Task
from superharness.providers.base import Provider, Tier
from superharness.skills.writer import Proposal, SkillWriter


class SkillLearner:
    def __init__(
        self,
        *,
        agents: AgentRegistry,
        provider: Provider,
        tiers: TierModelMap,
        writer: SkillWriter,
        hooks: HookBus | None = None,
        guidance_skill: str = "karpathy",
    ) -> None:
        self.agents = agents
        self.provider = provider
        self.tiers = tiers
        self.writer = writer
        self.hooks = hooks
        # 추출기 system 프롬프트 앞에 주입할 가이드 스킬(기본: karpathy 4원칙)
        self.guidance_skill = guidance_skill

    def _guidance_context(self) -> str:
        """가이드 스킬(예: karpathy)의 본문을 <skill> 블록으로 묶어 반환. 없으면 빈 문자열."""
        if not self.guidance_skill:
            return ""
        skill = self.writer.registry.get(self.guidance_skill)
        if skill is None:
            return ""
        return f'<skill name="{skill.name}">\n{skill.body}\n</skill>'

    async def learn(self, goal: str, trace: str, *, verified: bool) -> Proposal | None:
        """검증 통과 세션이면 learner로 스킬을 추출해 제안(격리)한다. 미통과면 None."""
        if not verified:
            return None  # Goal-Driven 게이트: 검증된 결과만 학습한다

        agent = self.agents.get("learner", Tier.HIGH)
        task = Task(
            id="learn",
            domain="learner",
            tier=Tier.HIGH,
            description=(
                f"목표: {goal}\n\n세션 트레이스:\n{trace}\n\n"
                "위 세션에서 '재사용 가능한 문제 해결 패턴' 1개를 추출해, "
                "YAML frontmatter(name·description·triggers·mode: plain) + 본문 마크다운으로만 "
                "출력하라. 일회성·프로젝트 특정 내용은 제외."
            ),
        )
        result = await agent.run(
            task,
            provider=self.provider,
            tiers=self.tiers,
            artifacts=None,
            hooks=self.hooks,
            injected_context=self._guidance_context(),  # karpathy 4원칙 주입
        )
        return self.writer.propose(result.output)
