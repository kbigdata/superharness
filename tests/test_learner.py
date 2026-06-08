"""SkillLearner — Goal-Driven 게이트 + 추출→제안 (오프라인)."""

from __future__ import annotations

from pathlib import Path

from superharness.agents import AgentRegistry
from superharness.config import TierModelMap
from superharness.orchestration import SkillLearner
from superharness.providers import MockProvider
from superharness.providers.base import CompletionRequest, CompletionResult
from superharness.skills import SkillRegistry, SkillWriter
from superharness.skills.writer import ProposalStatus

SKILL_MD = """---
name: extracted-pattern
description: 추출된 재사용 패턴
triggers: ["my special pattern"]
mode: plain
---
이렇게 해결한다.
"""


class _SkillMock:
    """learner 호출 시 유효한 스킬 마크다운을 돌려주는 결정적 프로바이더."""

    name = "skill-mock"

    async def complete(self, req: CompletionRequest) -> CompletionResult:
        return CompletionResult(text=SKILL_MD, model=req.model)


def _learner(tmp_path: Path, provider) -> SkillLearner:
    writer = SkillWriter(tmp_path / "skills", tmp_path / "skills-proposed", SkillRegistry.load())
    return SkillLearner(
        agents=AgentRegistry.default(), provider=provider, tiers=TierModelMap(), writer=writer
    )


async def test_learn_skips_when_unverified(tmp_path: Path):
    res = await _learner(tmp_path, _SkillMock()).learn("goal", "trace", verified=False)
    assert res is None  # Goal-Driven 게이트


async def test_learn_proposes_when_verified(tmp_path: Path):
    res = await _learner(tmp_path, _SkillMock()).learn("goal", "trace", verified=True)
    assert res is not None
    assert res.status == ProposalStatus.PROPOSED
    assert res.name == "extracted-pattern"


async def test_learner_injects_karpathy_guidance(tmp_path: Path):
    prov = MockProvider().when_fn(lambda r: True, SKILL_MD)   # 모든 호출에 유효 스킬 반환 + 기록
    res = await _learner(tmp_path, prov).learn("goal", "trace", verified=True)
    assert res is not None and res.status == ProposalStatus.PROPOSED
    # learner 에이전트 요청의 system 프롬프트에 karpathy 4원칙이 주입됐다
    assert prov.calls
    system = (prov.calls[-1].system or "").lower()
    assert 'skill name="karpathy"' in system
    assert "surgical" in system and "goal-driven" in system
