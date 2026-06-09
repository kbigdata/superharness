"""StateStore — control plane. 세션 메타와 project-memory.json을 다룬다 (작은 JSON)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from superharness.state.paths import StateLayout


class StateStore:
    """작은 운영 상태(control plane): 세션 생성/조회, project-memory 병합."""

    def __init__(self, layout: StateLayout) -> None:
        self.layout = layout
        self.layout.init()

    # --- 세션 ---
    def create_session(self, session_id: str) -> dict:
        d = self.layout.session_dir(session_id)
        d.mkdir(parents=True, exist_ok=True)
        meta = {
            "session_id": session_id,
            "created_at": datetime.now(UTC).isoformat(),
            "events": [],
        }
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        return meta

    def get_session(self, session_id: str) -> dict | None:
        path = self.layout.session_dir(session_id) / "meta.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def append_event(self, session_id: str, event: dict) -> None:
        path = self.layout.session_dir(session_id) / "meta.json"
        if not path.exists():
            self.create_session(session_id)
        meta = json.loads(path.read_text())
        meta.setdefault("events", []).append(event)
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    def search_sessions(self, query: str = "", *, since: str | None = None) -> list[dict]:
        """세션 meta.json을 스캔해 부분문자열/since로 필터한다(최신 우선).

        OMC의 `omc session search`에 대응. query는 직렬화된 meta(세션 id + events) 전체에 대해
        대소문자 무시 부분일치, since는 created_at ISO8601 비교.
        """
        base = self.layout.state / "sessions"
        if not base.is_dir():
            return []
        needle = query.lower()
        out: list[dict] = []
        for d in sorted(base.iterdir()):
            meta_path = d / "meta.json"
            if not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text())
            if needle and needle not in json.dumps(meta, ensure_ascii=False).lower():
                continue
            if since is not None and meta.get("created_at", "") < since:
                continue
            out.append(meta)
        out.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return out

    # --- project memory ---
    def read_memory(self) -> dict:
        path = self.layout.project_memory
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def merge_memory(self, updates: dict) -> dict:
        memory = self.read_memory()
        memory.update(updates)
        self._write_memory(memory)
        return memory

    def append_memory_event(self, event: dict) -> dict:
        """라이프사이클 이벤트를 project-memory의 'events' 리스트에 타임스탬프와 함께 적립한다.

        MemoryRecorder가 훅에서 호출하는 자동 축적 진입점. merge_memory(평면 사실)와 병존한다.
        """
        memory = self.read_memory()
        events = memory.setdefault("events", [])
        events.append({"at": datetime.now(UTC).isoformat(), **event})
        self._write_memory(memory)
        return memory

    def _write_memory(self, memory: dict) -> None:
        self.layout.project_memory.write_text(
            json.dumps(memory, ensure_ascii=False, indent=2)
        )
