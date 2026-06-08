"""스킬 의미 중복(semantic dedup) — 후보가 기존 스킬과 내용상 얼마나 겹치는지 점수화.

기본 구현 `LexicalSimilarity`는 description+triggers+body의 토큰 Jaccard로 오프라인·결정적
판정한다. `Similarity` Protocol이라 임베딩 등 다른 체커로 교체 가능.
(진짜 의미 판정은 learner의 LLM judge.)
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from superharness.skills.skill import Skill

_WORD = re.compile(r"\w+", re.UNICODE)


class SimilarityResult(BaseModel):
    best_name: str | None = None
    score: float = 0.0  # 0..1


@runtime_checkable
class Similarity(Protocol):
    def score(self, candidate: Skill, existing: list[Skill]) -> SimilarityResult: ...


def _tokens(skill: Skill) -> set[str]:
    fm = skill.frontmatter
    text = " ".join([fm.description, " ".join(fm.triggers), skill.body]).lower()
    return set(_WORD.findall(text))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


class LexicalSimilarity:
    """토큰 Jaccard 기반 오프라인 유사도. 후보와 가장 비슷한 기존 스킬 + 점수를 반환."""

    def score(self, candidate: Skill, existing: list[Skill]) -> SimilarityResult:
        ct = _tokens(candidate)
        best_name: str | None = None
        best = 0.0
        for s in existing:
            j = _jaccard(ct, _tokens(s))
            if j > best:
                best_name, best = s.name, j
        return SimilarityResult(best_name=best_name, score=best)
