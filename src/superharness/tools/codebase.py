"""Codebase — 읽기 전용 코드베이스 접근(glob/read/grep). 오프라인·표준 라이브러리만.

에이전트가 사용자 소스를 "이해"하도록 최소 도구를 제공한다. 모든 경로는 `as_read_path`로
검증해 루트 밖 접근(traversal)을 차단하고, 바이너리/대용량 파일은 건너뛴다.
"""

from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path

from pydantic import BaseModel

from superharness.errors import CodebaseError
from superharness.state.paths import as_read_path

# 탐색에서 제외하는 노이즈 디렉토리
_SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache", ".ruff_cache",
             ".pytest_cache", ".superharness", "dist", "build", ".idea", ".vscode"}
_DEFAULT_MAX_BYTES = 64_000


class GrepHit(BaseModel):
    """grep 매치 한 건."""

    path: str       # 루트 기준 상대 경로
    line: int       # 1-base 라인 번호
    text: str       # 매치된 라인(우측 공백 제거)


class Codebase:
    """루트 하위를 읽기 전용으로 탐색. 인스턴스는 한 코드베이스 루트에 바인딩된다."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise CodebaseError(f"코드베이스 루트가 디렉토리가 아님: {self.root}")

    def _iter_files(self) -> list[Path]:
        out: list[Path] = []
        for p in self.root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in _SKIP_DIRS for part in p.relative_to(self.root).parts):
                continue
            out.append(p)
        return out

    def _rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def glob(self, pattern: str) -> list[str]:
        """패턴에 매치되는 파일 상대경로 목록(정렬). 노이즈 디렉토리는 제외."""
        rels = [self._rel(p) for p in self._iter_files()]
        return sorted(r for r in rels if fnmatch(r, pattern))

    def read(self, rel: str, *, max_bytes: int = _DEFAULT_MAX_BYTES) -> str:
        """루트 하위 파일을 읽어 텍스트로 반환(최대 max_bytes). traversal은 PathViolation."""
        path = Path(as_read_path(self.root, rel))
        if not path.is_file():
            raise CodebaseError(f"파일 없음: {rel}")
        data = path.read_bytes()[:max_bytes]
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CodebaseError(f"바이너리/비UTF-8 파일: {rel}") from exc

    def grep(
        self,
        regex: str,
        *,
        include: str = "*",
        max_file_bytes: int = _DEFAULT_MAX_BYTES,
        max_hits: int = 200,
    ) -> list[GrepHit]:
        """정규식으로 라인 매칭. include glob로 파일을 한정, 바이너리/대용량은 skip."""
        try:
            pat = re.compile(regex)
        except re.error as exc:
            raise CodebaseError(f"잘못된 정규식: {regex!r} ({exc})") from exc

        hits: list[GrepHit] = []
        for p in self._iter_files():
            rel = self._rel(p)
            if not fnmatch(rel, include):
                continue
            try:
                text = p.read_bytes()[:max_file_bytes].decode("utf-8")
            except UnicodeDecodeError:
                continue  # 바이너리 skip
            for i, line in enumerate(text.splitlines(), start=1):
                if pat.search(line):
                    hits.append(GrepHit(path=rel, line=i, text=line.rstrip()))
                    if len(hits) >= max_hits:
                        return hits
        return hits

    def context_for(self, query: str, *, include: str = "*", max_hits: int = 20) -> str:
        """질의어를 포함한 라인들을 모아 주입용 <codebase> 블록으로 만든다(없으면 빈 문자열).

        injected_context로 에이전트에 코드 단서를 넣는 경로①(Provider 변경 없음)의 빌딩블록.
        """
        terms = [t for t in re.findall(r"\w+", query) if len(t) >= 3]
        if not terms:
            return ""
        pattern = "|".join(re.escape(t) for t in terms)
        hits = self.grep(pattern, include=include, max_hits=max_hits)
        if not hits:
            return ""
        lines = [f"{h.path}:{h.line}: {h.text}" for h in hits]
        return "<codebase>\n" + "\n".join(lines) + "\n</codebase>"
