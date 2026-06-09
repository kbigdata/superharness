from __future__ import annotations

from superharness.state.paths import StateLayout
from superharness.state.store import StateStore
from superharness.state.wiki import WikiStore


def test_wiki_append_and_render(layout: StateLayout):
    wiki = WikiStore(layout)
    wiki.append("CSV 파서", "따옴표 이스케이프 규칙을 기록")
    wiki.append("로그인 버그", "토큰 만료가 원인")

    rendered = wiki.render()
    assert "## CSV 파서" in rendered
    assert "## 로그인 버그" in rendered
    assert "따옴표" in rendered
    assert wiki.sections() == ["CSV 파서", "로그인 버그"]


def test_wiki_empty(layout: StateLayout):
    assert WikiStore(layout).render() == ""
    assert WikiStore(layout).sections() == []


def test_session_search_by_substring(store: StateStore):
    store.create_session("s-alpha")
    store.append_event("s-alpha", {"note": "team leader stale"})
    store.create_session("s-beta")
    store.append_event("s-beta", {"note": "all good"})

    hits = store.search_sessions("stale")
    assert [m["session_id"] for m in hits] == ["s-alpha"]
    # 빈 쿼리는 전체
    assert len(store.search_sessions("")) == 2


def test_session_search_since_filter(store: StateStore):
    store.create_session("s1")
    meta = store.get_session("s1")
    assert meta is not None
    # 생성 시각 이후로 필터하면 포함, 먼 미래로 필터하면 제외
    assert len(store.search_sessions("", since=meta["created_at"])) == 1
    assert store.search_sessions("", since="2999-01-01T00:00:00+00:00") == []


def test_session_search_empty_when_no_sessions(store: StateStore):
    assert store.search_sessions("anything") == []
