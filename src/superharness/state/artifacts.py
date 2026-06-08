"""ArtifactStore — data plane 저장소. 내용을 해시·기록하고 descriptor를 돌려준다."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from superharness.errors import StateError
from superharness.state.descriptor import ArtifactDescriptor
from superharness.state.paths import StateLayout, as_read_path, as_write_path

_EXT = {"plan": "md", "spec": "md", "result": "md", "trace": "json", "note": "md"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ArtifactStore:
    """큰 내구성 출력(plan/spec/result/trace)을 content-hash 주소로 저장한다."""

    def __init__(self, layout: StateLayout) -> None:
        self.layout = layout

    def write(self, kind: str, content: str, producer: str) -> ArtifactDescriptor:
        data = content.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        ext = _EXT.get(kind, "txt")
        rel = f"artifacts/{digest}.{ext}"
        path = as_write_path(self.layout.root, rel)
        path.write_bytes(data)
        return ArtifactDescriptor(
            kind=kind,
            path=str(path.relative_to(self.layout.root)),
            content_hash=digest,
            producer=producer,
            created_at=_now_iso(),
            size_bytes=len(data),
        )

    def read(self, descriptor: ArtifactDescriptor) -> str:
        path = as_read_path(self.layout.root, descriptor.path)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != descriptor.content_hash:
            raise StateError(
                f"아티팩트 해시 불일치: {descriptor.path} "
                f"(기대 {descriptor.content_hash[:12]}, 실제 {digest[:12]})"
            )
        return data.decode("utf-8")
