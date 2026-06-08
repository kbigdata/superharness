"""SkillVersionStore — 활성 스킬 내용의 버전 이력 + 롤백.

버전 = "활성 스킬 내용이 바뀐 이력". 내용은 ArtifactStore(content-hash, data plane)에 보관하고,
이름→버전 목록 인덱스는 작은 JSON(control plane)에 둔다. 자기개선(refine) 드리프트에 대비해
어느 버전으로든 롤백할 수 있게 한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from superharness.errors import StateError
from superharness.state.artifacts import ArtifactStore
from superharness.state.descriptor import ArtifactDescriptor


class VersionEntry(BaseModel):
    version: int
    operation: str  # promoted / rolledback / refined
    created_at: str
    descriptor: ArtifactDescriptor


class SkillVersionStore:
    def __init__(self, artifacts: ArtifactStore, index_path: Path) -> None:
        self.artifacts = artifacts
        self.index_path = Path(index_path)

    def _load(self) -> dict[str, list[dict]]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save(self, idx: dict) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def record(self, name: str, content: str, operation: str) -> VersionEntry:
        """스킬 내용을 아티팩트로 보관하고 버전 인덱스에 추가한다."""
        desc = self.artifacts.write("skill", content, producer=f"skill:{name}")
        idx = self._load()
        entries = idx.setdefault(name, [])
        entry = {
            "version": len(entries) + 1,
            "operation": operation,
            "created_at": desc.created_at,
            "descriptor": desc.model_dump(),
        }
        entries.append(entry)
        self._save(idx)
        return VersionEntry(**entry)

    def history(self, name: str) -> list[VersionEntry]:
        """버전 이력(최신 우선)."""
        return [VersionEntry(**e) for e in reversed(self._load().get(name, []))]

    def get(self, name: str, version: int) -> str:
        """특정 버전의 내용(해시 검증 포함)."""
        for e in self._load().get(name, []):
            if e["version"] == version:
                return self.artifacts.read(ArtifactDescriptor(**e["descriptor"]))
        raise StateError(f"버전 없음: {name}@{version}")
