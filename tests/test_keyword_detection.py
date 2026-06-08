from __future__ import annotations


def test_ultrawork_trigger(skills):
    matches = skills.detect("please ultrawork this refactor")
    names = {m.skill_name for m in matches}
    assert "ultrawork" in names


def test_ralph_multiword_trigger(skills):
    matches = skills.detect("implement it and don't stop until done")
    names = {m.skill_name for m in matches}
    assert "ralph" in names


def test_alias_triggers(skills):
    assert any(m.skill_name == "ultrawork" for m in skills.detect("run uw now"))


def test_no_trigger(skills):
    assert skills.detect("just a normal sentence about cats") == []


def test_activation_mode_is_strongest(skills):
    # ultrawork(ultrawork 모드) + ralph(ralph 모드) → 가장 강한 ralph 채택
    activation = skills.activate("ultrawork: build it, don't stop until done")
    assert activation.mode == "ralph"
    assert set(activation.skills) >= {"ultrawork", "ralph"}
    assert "<skill" in activation.injected_context
