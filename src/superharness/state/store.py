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

    # --- project memory ---
    def read_memory(self) -> dict:
        path = self.layout.project_memory
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def merge_memory(self, updates: dict) -> dict:
        memory = self.read_memory()
        memory.update(updates)
        self.layout.project_memory.write_text(
            json.dumps(memory, ensure_ascii=False, indent=2)
        )
        return memory
