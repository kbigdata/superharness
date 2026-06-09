"""WikiStore — 세션 누적형 마크다운 지식베이스.

레이아웃에 이미 있는 notepads/ 아래 wiki.md에 섹션 블록을 append한다.
OMC의 `wiki` 스킬(세션 누적 KB)에 대응하는 오프라인 구현.
"""

from __future__ import annotations

from datetime import UTC, datetime

from superharness.state.paths import StateLayout


class WikiStore:
    """notepads/wiki.md 누적 KB. append로 섹션 블록 추가, render로 전체 마크다운 반환."""

    def __init__(self, layout: StateLayout) -> None:
        self._path = layout.notepads / "wiki.md"

    def append(self, section: str, text: str) -> str:
        """`## {section}` 블록을 타임스탬프와 함께 추가한다."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).isoformat()
        block = f"## {section}\n_{ts}_\n\n{text}\n"
        existing = self._path.read_text(encoding="utf-8") if self._path.exists() else ""
        body = (existing + "\n" + block) if existing else block
        self._path.write_text(body, encoding="utf-8")
        return block

    def render(self) -> str:
        """누적된 위키 전체를 반환(없으면 빈 문자열)."""
        return self._path.read_text(encoding="utf-8") if self._path.exists() else ""

    def sections(self) -> list[str]:
        """등록된 섹션 제목 목록(등장 순)."""
        return [
            ln[3:].strip()
            for ln in self.render().splitlines()
            if ln.startswith("## ")
        ]
