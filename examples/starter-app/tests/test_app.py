"""스타터 앱 스모크 테스트 — 전부 오프라인(mock)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_app.app import build_agents, build_skills, run_goal, run_reviewer


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch):
    # 상태 디렉토리를 테스트별 임시 경로로 격리
    monkeypatch.setenv("SUPERHARNESS_STATE_DIR", str(tmp_path / ".superharness"))
    monkeypatch.setenv("SUPERHARNESS_PROVIDER", "mock")


def test_custom_skill_loaded():
    names = {s.name for s in build_skills().skills}
    assert "review" in names                    # 앱 전용 스킬
    assert {"ultrawork", "ralph"} <= names       # builtin 도 함께


def test_custom_agent_registered():
    agent = build_agents().get_by_name("reviewer")
    assert agent.spec.domain == "reviewer"


async def test_run_goal_team_pipeline():
    activation, result = await run_goal("code review: tighten the CSV parser")
    assert "review" in activation.skills          # 키워드 활성화
    assert result.verified is True                # mock → 1회 통과
    assert result.plan is not None
    assert len(result.results) >= 1


async def test_run_reviewer_single_dispatch():
    res = await run_reviewer("def f(x): return x+1  # 리뷰해")
    assert res.agent == "reviewer"
    assert res.output
    assert res.artifact is not None
