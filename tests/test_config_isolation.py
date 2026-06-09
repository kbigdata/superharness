from __future__ import annotations

from pathlib import Path

from superharness.config import Settings, derive_project_id


def test_default_keeps_state_dir_backward_compatible():
    s = Settings(state_dir="./.superharness")
    assert s.state_dir == "./.superharness"
    assert s.project_id is None


def test_state_root_derives_per_project_dir():
    s = Settings(state_root="/tmp/sh-root", project_id="proj-a")
    assert s.state_dir == str(Path("/tmp/sh-root") / "proj-a")
    assert s.project_id == "proj-a"


def test_state_root_auto_derives_project_id_when_absent():
    s = Settings(state_root="/tmp/sh-root")
    assert s.project_id is not None and len(s.project_id) == 12
    assert s.state_dir == str(Path("/tmp/sh-root") / s.project_id)


def test_different_projects_isolate():
    a = Settings(state_root="/tmp/sh-root", project_id="a")
    b = Settings(state_root="/tmp/sh-root", project_id="b")
    assert a.state_dir != b.state_dir


def test_derive_project_id_is_deterministic(tmp_path: Path):
    assert derive_project_id(tmp_path) == derive_project_id(tmp_path)
    assert len(derive_project_id(tmp_path)) == 12
