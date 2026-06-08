"""SkillInjector — 매칭된 스킬을 활성화해 주입 컨텍스트와 실행 모드를 만든다.

스킬 주입의 in-process 구현.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from superharness.skills.keyword_detector import MatchedTrigger
from superharness.skills.skill import Mode, Skill

# 모드 우선순위 — 여러 스킬이 활성화되면 가장 강한 모드를 채택
_MODE_RANK: dict[Mode, int] = {
    "plain": 0,
    "ultrawork": 1,
    "autopilot": 2,
    "team": 3,
    "ralph": 4,
}


class Activation(BaseModel):
    """활성화 결과: 적용된 스킬들 + 주입 컨텍스트 + 결정된 모드."""

    skills: list[str] = Field(default_factory=list)
    injected_context: str = ""
    mode: Mode = "plain"
    pipeline: list[str] | None = None


class SkillInjector:
    def __init__(self, skills: list[Skill]) -> None:
        self._by_name = {s.name: s for s in skills}

    def activate(self, matches: list[MatchedTrigger]) -> Activation:
        applied: list[Skill] = []
        for m in matches:
            skill = self._by_name.get(m.skill_name)
            if skill and skill not in applied:
                applied.append(skill)

        if not applied:
            return Activation()

        blocks = [
            f'<skill name="{s.name}">\n{s.body}\n</skill>' for s in applied
        ]
        mode = max(
            (s.frontmatter.mode for s in applied),
            key=lambda mo: _MODE_RANK.get(mo, 0),
        )
        pipeline = next(
            (s.frontmatter.pipeline for s in applied if s.frontmatter.pipeline), None
        )
        return Activation(
            skills=[s.name for s in applied],
            injected_context="\n\n".join(blocks),
            mode=mode,
            pipeline=pipeline,
        )
