from __future__ import annotations

from pathlib import Path

import pytest

from superharness.tools.codebase import Codebase
from superharness.tools.codemap import CodeMap


@pytest.fixture
def py_root(tmp_path: Path) -> Path:
    (tmp_path / "mod.py").write_text(
        '"""모듈 독스트링.\n\n둘째 줄."""\n\n'
        "import os\n\n"
        "class Foo:\n    def method(self):\n        pass\n\n"
        "def top_fn():\n    return 1\n\n"
        "async def top_async():\n    return 2\n",
        encoding="utf-8",
    )
    (tmp_path / "broken.py").write_text("def (((\n", encoding="utf-8")  # 파싱 실패
    (tmp_path / "note.txt").write_text("not python\n", encoding="utf-8")
    return tmp_path


def test_build_extracts_top_level_symbols(py_root: Path):
    maps = {fm.path: fm for fm in CodeMap(Codebase(py_root)).build()}
    mod = maps["mod.py"]
    names = {(s.kind, s.name) for s in mod.symbols}
    assert ("class", "Foo") in names
    assert ("def", "top_fn") in names
    assert ("async def", "top_async") in names
    # 클래스 메서드는 top-level이 아니므로 제외
    assert ("def", "method") not in names
    assert mod.docstring is not None and mod.docstring.startswith("모듈 독스트링")


def test_broken_file_listed_without_symbols(py_root: Path):
    maps = {fm.path: fm for fm in CodeMap(Codebase(py_root)).build()}
    assert "broken.py" in maps
    assert maps["broken.py"].symbols == []


def test_include_filter_excludes_non_python(py_root: Path):
    maps = CodeMap(Codebase(py_root)).build(include="*.py")
    assert "note.txt" not in {fm.path for fm in maps}


def test_render_markdown(py_root: Path):
    md = CodeMap(Codebase(py_root)).render()
    assert md.startswith("# 코드맵:")
    assert "- `mod.py`" in md
    assert "class `Foo`" in md
    assert "async def `top_async`" in md
