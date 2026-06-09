"""구조화 메모리 — namespace/tags/timestamp가 있는 MemoryEntry + 오프라인 검색/회상.

평면 project-memory.json(작은 사실)을 부수지 않고 별도 memory.json(entries[])로 확장한다.
검색은 namespace/tag/since/부분문자열 필터 + 토큰 Jaccard 랭킹(임베딩 없이, 결정적).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from superharness.state.paths import StateLayout

_WORD = re.compile(r"\w+", re.UNICODE)
# 한글/한자 연속 구간 — 조사·어미가 붙는 CJK는 단어 토큰만으론 매칭이 약해
# 문자 bigram을 함께 써서 부분 일치를 잡는다(예: "파서는" ↔ "파서").
_CJK = re.compile(r"[가-힣一-鿿]+")


def _tokens(text: str) -> set[str]:
    low = text.lower()
    toks = set(_WORD.findall(low))
    for run in _CJK.findall(low):
        if len(run) == 1:
            toks.add(run)
        toks.update(run[i : i + 2] for i in range(len(run) - 1))
    return toks


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


class MemoryEntry(BaseModel):
    """회상 가능한 메모리 한 조각."""

    id: str
    namespace: str = "default"
    text: str
    tags: list[str] = Field(default_factory=list)
    created_at: str
    source: str = ""


class MemoryStore:
    """memory.json(entries[])에 대한 추가/조회/검색/회상. 오프라인·결정적."""

    def __init__(self, layout: StateLayout) -> None:
        self.layout = layout
        self._path = layout.root / "memory.json"

    def _load(self) -> list[MemoryEntry]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return [MemoryEntry(**e) for e in raw]

    def _save(self, entries: list[MemoryEntry]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([e.model_dump() for e in entries], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(
        self,
        text: str,
        *,
        namespace: str = "default",
        tags: list[str] | None = None,
        source: str = "",
    ) -> MemoryEntry:
        """메모리를 추가한다. id는 (namespace+text) 해시 — 같은 내용 재추가는 같은 id."""
        digest = hashlib.sha256(f"{namespace}\x00{text}".encode()).hexdigest()[:12]
        entry = MemoryEntry(
            id=digest,
            namespace=namespace,
            text=text,
            tags=tags or [],
            created_at=datetime.now(UTC).isoformat(),
            source=source,
        )
        entries = self._load()
        # 동일 id가 있으면 갱신, 없으면 추가 (idempotent)
        entries = [e for e in entries if e.id != entry.id]
        entries.append(entry)
        self._save(entries)
        return entry

    def all(self) -> list[MemoryEntry]:
        return self._load()

    def query(
        self,
        *,
        namespace: str | None = None,
        tags: list[str] | None = None,
        text_contains: str | None = None,
        since: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryEntry]:
        """필터 검색(최신 우선). 모든 조건은 AND. since는 ISO8601 문자열 비교."""
        out = self._load()
        if namespace is not None:
            out = [e for e in out if e.namespace == namespace]
        if tags:
            tagset = set(tags)
            out = [e for e in out if tagset.issubset(set(e.tags))]
        if text_contains:
            needle = text_contains.lower()
            out = [e for e in out if needle in e.text.lower()]
        if since is not None:
            out = [e for e in out if e.created_at >= since]
        out.sort(key=lambda e: e.created_at, reverse=True)
        return out[:limit] if limit is not None else out

    def recall(
        self, prompt: str, *, namespace: str | None = None, top_k: int = 3
    ) -> list[MemoryEntry]:
        """프롬프트와 토큰 Jaccard가 높은 메모리 top_k(겹침 0 제외)."""
        pt = _tokens(prompt)
        if not pt:
            return []
        pool = self.query(namespace=namespace) if namespace else self._load()
        scored = [(e, _jaccard(pt, _tokens(e.text))) for e in pool]
        scored = [(e, s) for e, s in scored if s > 0.0]
        scored.sort(key=lambda es: es[1], reverse=True)
        return [e for e, _ in scored[:top_k]]


class MemoryInjector:
    """회상된 메모리를 task 컨텍스트(<memory> 블록)로 만든다. SkillInjector와 대칭."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def recall(self, prompt: str, *, namespace: str | None = None, top_k: int = 3) -> str:
        hits = self._store.recall(prompt, namespace=namespace, top_k=top_k)
        if not hits:
            return ""
        lines = [f"- {e.text}" for e in hits]
        return "<memory>\n" + "\n".join(lines) + "\n</memory>"
