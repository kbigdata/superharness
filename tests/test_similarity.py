"""의미 중복(semantic dedup) — 어휘 유사도 + propose 게이트 (오프라인)."""

from __future__ import annotations

from pathlib import Path

from superharness.skills import LexicalSimilarity, SkillRegistry, SkillWriter, load_skill_text
from superharness.skills.writer import ProposalStatus

# builtin 'ralph'와 내용이 거의 같지만 name·트리거는 다른 후보(정확 dedup은 통과)
NEAR_RALPH = """---
name: keep-going
description: 검증 완료까지 멈추지 않는 지속/검증 루프
triggers: ["never halt", "keep going"]
mode: plain
---
목표가 검증으로 완료될 때까지 verify→fix 루프를 반복한다.
부분 완료로 종료하지 않으며, 실패한 항목만 다시 실행해 재검증한다 (persistence 모드).
"""

DISTINCT = """---
name: csv-helper
description: CSV 파싱 유틸 작성
triggers: ["parse csv", "csv util"]
mode: plain
---
콤마 구분 파일을 안전하게 읽는 헬퍼를 만든다.
"""


def test_lexical_similarity_scores_near_duplicate_high():
    reg = SkillRegistry.load()
    sim = LexicalSimilarity()
    near = sim.score(load_skill_text(NEAR_RALPH), reg.skills)
    distinct = sim.score(load_skill_text(DISTINCT), reg.skills)
    assert near.best_name == "ralph"
    assert near.score > distinct.score
    assert near.score >= 0.6 > distinct.score


def _writer(tmp_path: Path) -> SkillWriter:
    return SkillWriter(tmp_path / "skills", tmp_path / "skills-proposed", SkillRegistry.load())


def test_propose_rejects_semantic_duplicate(tmp_path: Path):
    p = _writer(tmp_path).propose(NEAR_RALPH)   # ralph와 의미 중복
    assert p.status == ProposalStatus.REJECTED_DUPLICATE
    assert "semantic duplicate" in p.reason


def test_propose_accepts_distinct(tmp_path: Path):
    assert _writer(tmp_path).propose(DISTINCT).status == ProposalStatus.PROPOSED


def test_threshold_is_configurable(tmp_path: Path):
    # 임계치를 0.99로 올리면 near-duplicate도 통과(격리)된다
    w = SkillWriter(
        tmp_path / "skills",
        tmp_path / "skills-proposed",
        SkillRegistry.load(),
        similarity_threshold=0.99,
    )
    assert w.propose(NEAR_RALPH).status == ProposalStatus.PROPOSED
