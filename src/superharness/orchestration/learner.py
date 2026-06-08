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
from superharness.skills.skill import Skill
from superharness.skills.writer import Proposal, ProposalStatus, SkillWriter


def _skill_to_md(skill: Skill) -> str:
    """Skill 객체를 frontmatter 마크다운으로 직렬화 (critic 입력용)."""
    fm = skill.frontmatter
    triggers = ", ".join(f'"{t}"' for t in fm.triggers)
    return (
        f"---\nname: {fm.name}\ndescription: {fm.description}\n"
        f"triggers: [{triggers}]\nmode: {fm.mode}\n---\n{skill.body}"
    )


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
        semantic_judge: bool = False,
        judge_domain: str = "critic",
    ) -> None:
        self.agents = agents
        self.provider = provider
        self.tiers = tiers
        self.writer = writer
        self.hooks = hooks
        # 추출기 system 프롬프트 앞에 주입할 가이드 스킬(기본: karpathy 4원칙)
        self.guidance_skill = guidance_skill
        # 추출 후 LLM이 의미 중복을 판정(opt-in). writer의 오프라인 어휘 게이트와 별개.
        self.semantic_judge = semantic_judge
        self.judge_domain = judge_domain

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
        if self.semantic_judge:
            dup = await self._semantic_duplicate(result.output)
            if dup is not None:
                return Proposal(
                    status=ProposalStatus.REJECTED_DUPLICATE,
                    reason=f"semantic duplicate of {dup!r} (LLM judge)",
                )
        return self.writer.propose(result.output)

    async def _semantic_duplicate(self, candidate_md: str) -> str | None:
        """LLM 판정: 후보가 기존 스킬과 의미상 중복이면 그 이름, 고유하면 None."""
        existing = self.writer.registry.skills
        if not existing:
            return None
        listing = "\n".join(f"- {s.name}: {s.frontmatter.description}" for s in existing)
        judge = self.agents.get(self.judge_domain, Tier.HIGH)
        task = Task(
            id="dedup-judge",
            domain=self.judge_domain,
            tier=Tier.HIGH,
            description=(
                f"후보 스킬:\n{candidate_md}\n\n기존 스킬 목록:\n{listing}\n\n"
                "후보가 기존 중 하나와 '의미상 중복'이면 'DUPLICATE: <name>' 한 줄로, "
                "고유하면 'UNIQUE' 한 줄로만 답하라."
            ),
        )
        res = await judge.run(
            task, provider=self.provider, tiers=self.tiers, artifacts=None, hooks=self.hooks
        )
        out = res.output.strip()
        if out.upper().startswith("DUPLICATE"):
            name = out.split(":", 1)[1].strip() if ":" in out else ""
            return name or "(unknown)"
        return None

    async def refine(self, name: str, note: str = "") -> Proposal | None:
        """기존 활성 스킬을 critic으로 개선한 후보를 격리(제안)한다. 없는 스킬이면 None.

        개선안은 동일 name을 유지하며 proposed에 격리된다 — 승격(promote) 시 버전으로 기록.
        드리프트에 대비해 rollback이 가능하다.
        """
        existing = self.writer.registry.get(name)
        if existing is None:
            return None
        critic = self.agents.get("critic", Tier.HIGH)
        default_note = "더 간결·정확하게 다듬되 동일 name·핵심 트리거를 유지하라."
        task = Task(
            id="refine",
            domain="critic",
            tier=Tier.HIGH,
            description=(
                f"기존 스킬:\n{_skill_to_md(existing)}\n\n"
                f"개선 요청: {note or default_note}\n\n"
                f"개선된 스킬 1개를 YAML frontmatter 마크다운으로만 출력하라. name은 '{name}' 유지."
            ),
        )
        result = await critic.run(
            task,
            provider=self.provider,
            tiers=self.tiers,
            artifacts=None,
            hooks=self.hooks,
            injected_context=self._guidance_context(),
        )
        return self.writer.propose(result.output, refine=True)
