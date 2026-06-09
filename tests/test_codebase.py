from __future__ import annotations

from pathlib import Path

import pytest

from superharness.errors import CodebaseError, PathViolation
from superharness.tools.codebase import Codebase


@pytest.fixture
def sample_root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "parser.py").write_text(
        "def parse(line):\n    # CSV 따옴표 이스케이프 처리\n    return line\n", encoding="utf-8"
    )
    (tmp_path / "src" / "util.py").write_text("def noop():\n    pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# 데모\nCSV 파서 데모\n", encoding="utf-8")
    # 노이즈 디렉토리는 제외되어야 함
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("CSV\n", encoding="utf-8")
    # 바이너리 파일 — grep에서 skip
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02CSV\xff")
    return tmp_path


def test_glob_lists_files_and_skips_noise(sample_root: Path):
    cb = Codebase(sample_root)
    py = cb.glob("*.py")
    assert "src/parser.py" in py
    assert "src/util.py" in py
    # .git 아래는 제외
    assert all(not r.startswith(".git/") for r in cb.glob("*"))


def test_read_returns_text(sample_root: Path):
    cb = Codebase(sample_root)
    assert "def parse" in cb.read("src/parser.py")


def test_read_traversal_blocked(sample_root: Path):
    cb = Codebase(sample_root)
    with pytest.raises(PathViolation):
        cb.read("../etc/passwd")


def test_read_binary_raises(sample_root: Path):
    cb = Codebase(sample_root)
    with pytest.raises(CodebaseError):
        cb.read("blob.bin")


def test_grep_matches_and_skips_binary_and_noise(sample_root: Path):
    cb = Codebase(sample_root)
    hits = cb.grep("CSV")
    paths = {h.path for h in hits}
    assert "src/parser.py" in paths
    assert "README.md" in paths
    assert "blob.bin" not in paths          # 바이너리 skip
    assert ".git/config" not in paths       # 노이즈 skip


def test_grep_include_filter(sample_root: Path):
    cb = Codebase(sample_root)
    hits = cb.grep("CSV", include="*.py")
    assert {h.path for h in hits} == {"src/parser.py"}


def test_context_for_builds_block(sample_root: Path):
    cb = Codebase(sample_root)
    block = cb.context_for("CSV 파서 이스케이프", include="*.py")
    assert block.startswith("<codebase>")
    assert "src/parser.py" in block

    assert cb.context_for("zzzznomatch") == ""


def test_invalid_root_raises(tmp_path: Path):
    with pytest.raises(CodebaseError):
        Codebase(tmp_path / "does-not-exist")
