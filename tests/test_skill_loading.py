from __future__ import annotations

import pytest

from superharness.errors import SkillError
from superharness.skills.skill import load_skill_text


def test_frontmatter_parsing():
    text = (
        "---\n"
        "name: demo\n"
        "description: a demo\n"
        "triggers: ['go', 'run it']\n"
        "mode: team\n"
        "---\n"
        "do the thing"
    )
    skill = load_skill_text(text)
    assert skill.name == "demo"
    assert skill.frontmatter.mode == "team"
    assert "run it" in skill.frontmatter.triggers
    assert skill.body == "do the thing"


def test_missing_frontmatter_raises():
    with pytest.raises(SkillError):
        load_skill_text("no frontmatter here")


def test_builtin_skills_loaded(skills):
    names = {s.name for s in skills.skills}
    assert {"ultrawork", "autopilot", "ralph", "team", "karpathy"} <= names


def test_karpathy_skill_loads_and_activates(skills):
    s = skills.get("karpathy")
    assert s is not None
    assert s.frontmatter.mode == "plain"            # 항상 주입되는 가이드(모드 미덮어씀)
    matches = skills.detect("apply karpathy discipline")
    assert any(m.skill_name == "karpathy" for m in matches)
    # 본문에 4원칙이 모두 담겨 있다
    body = s.body.lower()
    for kw in ("think before", "simplicity", "surgical", "goal-driven"):
        assert kw in body
