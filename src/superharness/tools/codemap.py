"""CodeMap — deepinit식 코드 구조 요약(파일별 top-level 심볼). 순수 표준 라이브러리(ast).

OMC의 `deepinit`(계층형 AGENTS.md 생성)에 대응하는 오프라인·무의존성 코어. 네이티브
애드온(ast-grep) 없이 파이썬 `ast` 모듈로 클래스/함수 심볼을 추출해 마크다운 코드맵을 만든다.
정밀 LSP/AST 네비게이션은 선택적 extra로 분리(후순위).
"""

from __future__ import annotations

import ast

from pydantic import BaseModel, Field

from superharness.tools.codebase import Codebase

# ast 파싱용으로 충분히 큰 읽기 상한(truncation으로 인한 파싱 실패 방지)
_PARSE_MAX_BYTES = 2_000_000


class SymbolInfo(BaseModel):
    kind: str   # "class" | "def" | "async def"
    name: str
    lineno: int


class FileMap(BaseModel):
    path: str
    docstring: str | None = None
    symbols: list[SymbolInfo] = Field(default_factory=list)


def _symbols(tree: ast.Module) -> list[SymbolInfo]:
    out: list[SymbolInfo] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out.append(SymbolInfo(kind="class", name=node.name, lineno=node.lineno))
        elif isinstance(node, ast.FunctionDef):
            out.append(SymbolInfo(kind="def", name=node.name, lineno=node.lineno))
        elif isinstance(node, ast.AsyncFunctionDef):
            out.append(SymbolInfo(kind="async def", name=node.name, lineno=node.lineno))
    return out


class CodeMap:
    """코드베이스의 파이썬 파일에서 top-level 심볼을 추출해 구조 맵을 만든다."""

    def __init__(self, codebase: Codebase) -> None:
        self.codebase = codebase

    def build(self, *, include: str = "*.py") -> list[FileMap]:
        """include glob 매치 파일들의 FileMap 목록(경로순). 파싱 실패 파일은 심볼 없이 포함."""
        maps: list[FileMap] = []
        for rel in self.codebase.glob(include):
            try:
                source = self.codebase.read(rel, max_bytes=_PARSE_MAX_BYTES)
                tree = ast.parse(source)
            except Exception:  # noqa: BLE001 - 깨진/바이너리 파일은 건너뛰되 목록엔 남김
                maps.append(FileMap(path=rel))
                continue
            maps.append(
                FileMap(path=rel, docstring=ast.get_docstring(tree), symbols=_symbols(tree))
            )
        return maps

    def render(self, *, include: str = "*.py") -> str:
        """코드맵을 마크다운으로 렌더링한다 (deepinit/AGENTS.md 스타일)."""
        lines = [f"# 코드맵: {self.codebase.root.name}", ""]
        for fm in self.build(include=include):
            lines.append(f"- `{fm.path}`")
            if fm.docstring:
                summary = fm.docstring.strip().splitlines()[0]
                lines.append(f"  > {summary}")
            for s in fm.symbols:
                lines.append(f"  - {s.kind} `{s.name}` (L{s.lineno})")
        return "\n".join(lines) + "\n"
