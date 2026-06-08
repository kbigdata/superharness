"""스킬 버전 이력 + 롤백 (오프라인)."""

from __future__ import annotations

from pathlib import Path

from superharness.skills import SkillRegistry, SkillVersionStore, SkillWriter
from superharness.state import ArtifactStore, StateLayout


def _md(body: str) -> str:
    fm = '---\nname: vskill\ndescription: d\ntriggers: ["vskill trigger"]\nmode: plain\n---\n'
    return f"{fm}{body}\n"


def _wire(tmp_path: Path) -> tuple[SkillWriter, SkillVersionStore]:
    layout = StateLayout(tmp_path / ".superharness").init()
    versions = SkillVersionStore(ArtifactStore(layout), layout.root / "skill-versions.json")
    writer = SkillWriter(
        tmp_path / "skills", tmp_path / "skills-proposed", SkillRegistry.load(), versions=versions
    )
    return writer, versions


def test_version_store_record_history_get(tmp_path: Path):
    layout = StateLayout(tmp_path / ".superharness").init()
    vs = SkillVersionStore(ArtifactStore(layout), layout.root / "skill-versions.json")
    e1 = vs.record("vskill", "content one", "promoted")
    e2 = vs.record("vskill", "content two", "refined")
    assert (e1.version, e2.version) == (1, 2)
    assert [h.version for h in vs.history("vskill")] == [2, 1]   # 최신 우선
    assert vs.get("vskill", 1) == "content one"
    assert vs.get("vskill", 2) == "content two"


def test_promote_records_version(tmp_path: Path):
    writer, _ = _wire(tmp_path)
    writer.propose(_md("v1 body"))
    writer.promote("vskill")
    hist = writer.history("vskill")
    assert len(hist) == 1
    assert hist[0].operation == "promoted"


def test_rollback_restores_and_records(tmp_path: Path):
    writer, _ = _wire(tmp_path)
    writer.propose(_md("body one"))
    writer.promote("vskill")                              # v1
    writer.propose(_md("body two"), refine=True)          # 같은 name 개선안 격리
    writer.promote("vskill")                              # v2
    active = tmp_path / "skills" / "vskill.md"
    assert "body two" in active.read_text()

    writer.rollback("vskill", 1)                          # v1로 롤백 → v3 기록
    assert "body one" in active.read_text()
    ops = [h.operation for h in writer.history("vskill")]
    assert ops == ["rolledback", "promoted", "promoted"]  # 최신 우선
