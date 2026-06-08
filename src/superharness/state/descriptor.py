"""ArtifactDescriptor — data plane 참조 객체.

control plane은 descriptor만 들고 다니고, 큰 내용은 data plane(디스크)에 남긴다.
descriptor 필드 규약: kind, path, content_hash, created_at, producer, ...
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArtifactDescriptor(BaseModel):
    """디스크 아티팩트에 대한 경량 메타데이터 참조."""

    kind: str
    path: str
    content_hash: str
    producer: str
    created_at: str
    size_bytes: int | None = None
    expires_at: str | None = None

    model_config = {"frozen": True}


class TaskRef(BaseModel):
    """control plane에서 아티팩트를 가리키는 참조 + 라벨."""

    descriptor: ArtifactDescriptor
    label: str = Field(default="")
