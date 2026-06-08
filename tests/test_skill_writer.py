"""SkillWriter 게이트 — 검증·안전성·dedup·격리·승격 (전부 오프라인)."""

from __future__ import annotations

from pathlib import Path

from superharness.skills import SkillRegistry, SkillWriter
from superharness.skills.writer import ProposalStatus

VALID = """---
name: fix-proxy
description: aiohttp proxy crash 처리
triggers: ["proxy crash", "aiohttp disconnect"]
mode: plain
---
server.py 핸들러를 try/except로 감싼다.
"""


def _writer(tmp_path: Path) -> SkillWriter:
    return SkillWriter(tmp_path / "skills", tmp_path / "skills-proposed", SkillRegistry.load())


def test_propose_valid_is_quarantined(tmp_path: Path):
    w = _writer(tmp_path)
    p = w.propose(VALID)
    assert p.status == ProposalStatus.PROPOSED
    assert "fix-proxy" in w.list_proposed()
    # 격리 디렉토리에만 있고, 자동 로드되는 활성 디렉토리에는 없다
    assert (tmp_path / "skills-proposed" / "fix-proxy.md").exists()
    assert not (tmp_path / "skills" / "fix-proxy.md").exists()


def test_reject_invalid(tmp_path: Path):
    p = _writer(tmp_path).propose("no frontmatter here")
    assert p.status == ProposalStatus.REJECTED_INVALID


def test_reject_unsafe(tmp_path: Path):
    bad = VALID.replace("server.py 핸들러를", "print(ANTHROPIC_API_KEY)  # 핸들러를")
    assert _writer(tmp_path).propose(bad).status == ProposalStatus.REJECTED_UNSAFE


def test_reject_duplicate_name(tmp_path: Path):
    dup = VALID.replace("name: fix-proxy", "name: ralph")  # builtin 'ralph' 존재
    assert _writer(tmp_path).propose(dup).status == ProposalStatus.REJECTED_DUPLICATE


def test_reject_trigger_collision(tmp_path: Path):
    coll = VALID.replace(
        'triggers: ["proxy crash", "aiohttp disconnect"]', 'triggers: ["ultrawork"]'
    )  # builtin ultrawork 트리거와 충돌
    assert _writer(tmp_path).propose(coll).status == ProposalStatus.REJECTED_DUPLICATE


def test_promote_makes_loadable(tmp_path: Path):
    w = _writer(tmp_path)
    w.propose(VALID)
    dst = w.promote("fix-proxy")
    assert dst.exists()
    assert not (tmp_path / "skills-proposed" / "fix-proxy.md").exists()
    # 승격된 활성 디렉토리를 로드하면 스킬이 잡힌다
    reg = SkillRegistry.load(extra_dirs=[tmp_path / "skills"])
    assert reg.get("fix-proxy") is not None
