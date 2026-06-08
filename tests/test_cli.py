"""CLI 스모크 테스트 — typer CliRunner로 각 명령을 오프라인(mock) 실행."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from superharness.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERHARNESS_STATE_DIR", str(tmp_path / ".superharness"))
    monkeypatch.setenv("SUPERHARNESS_PROVIDER", "mock")
    monkeypatch.setenv("SUPERHARNESS_LOG", "ERROR")


def test_ask_routes_tier_to_model():
    r = runner.invoke(app, ["ask", "hello", "--tier", "high"])
    assert r.exit_code == 0
    assert "claude-opus-4-8" in r.stdout       # HIGH → opus 라우팅


def test_skills_list():
    r = runner.invoke(app, ["skills", "list"])
    assert r.exit_code == 0
    assert "ultrawork" in r.stdout


def test_skills_detect():
    r = runner.invoke(app, ["skills", "detect", "ultrawork: go, don't stop until done"])
    assert r.exit_code == 0
    assert "ralph" in r.stdout


def test_state_init():
    r = runner.invoke(app, ["state", "init"])
    assert r.exit_code == 0
    assert "상태 디렉토리" in r.stdout


def test_agents_run():
    r = runner.invoke(app, ["agents", "run", "executor", "do x"])
    assert r.exit_code == 0
    assert "executor" in r.stdout


def test_team():
    r = runner.invoke(app, ["team", "build a parser"])
    assert r.exit_code == 0
    assert "검증 완료" in r.stdout


def test_demo():
    r = runner.invoke(app, ["demo"])
    assert r.exit_code == 0
    assert "검증 완료" in r.stdout
