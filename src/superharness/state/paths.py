"""브랜디드 ReadPath/WritePath + 상태 디렉토리 레이아웃.

ReadPath/WritePath 규율: NewType으로 정적 구분 + 검증 생성자로
런타임 traversal 차단. 리더는 ReadPath를, 라이터는 WritePath를 받도록 시그니처를 잡으면
mypy가 교차 대입을 거부한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import NewType

from superharness.errors import PathViolation

ReadPath = NewType("ReadPath", Path)
WritePath = NewType("WritePath", Path)


def _resolve_under(root: Path, target: str | Path) -> Path:
    root = root.resolve()
    target = Path(target)
    candidate = (target if target.is_absolute() else root / target).resolve()
    if root not in candidate.parents and candidate != root:
        raise PathViolation(f"경로가 상태 루트를 벗어남: {candidate} (루트: {root})")
    return candidate


def as_read_path(root: Path, target: str | Path) -> ReadPath:
    """상태 루트 하위로 해석된, 읽기 전용 의미의 검증된 경로."""
    return ReadPath(_resolve_under(root, target))


def as_write_path(root: Path, target: str | Path) -> WritePath:
    """상태 루트 하위로 해석된, 쓰기 의미의 검증된 경로. 부모 디렉토리를 생성한다."""
    path = _resolve_under(root, target)
    path.parent.mkdir(parents=True, exist_ok=True)
    return WritePath(path)


class StateLayout:
    """`.superharness/` 스타일 상태 트리. control/data plane 분리 레이아웃."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    # control plane (작은 메타/큐/세션)
    @property
    def state(self) -> Path:
        return self.root / "state"

    def session_dir(self, session_id: str) -> Path:
        return self.state / "sessions" / session_id

    @property
    def project_memory(self) -> Path:
        return self.root / "project-memory.json"

    # data plane (큰 내구성 아티팩트)
    @property
    def specs(self) -> Path:
        return self.root / "specs"

    @property
    def plans(self) -> Path:
        return self.root / "plans"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def notepads(self) -> Path:
        return self.root / "notepads"

    @property
    def handoffs(self) -> Path:
        return self.root / "handoffs"

    def init(self) -> StateLayout:
        """전체 트리를 생성한다 (idempotent)."""
        for d in (
            self.state,
            self.state / "sessions",
            self.specs,
            self.plans,
            self.artifacts,
            self.notepads,
            self.handoffs,
        ):
            d.mkdir(parents=True, exist_ok=True)
        return self
