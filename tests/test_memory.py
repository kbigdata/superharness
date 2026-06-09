from __future__ import annotations

from superharness.state.memory import MemoryInjector, MemoryStore
from superharness.state.paths import StateLayout


def test_add_and_query_by_namespace_and_tag(layout: StateLayout):
    store = MemoryStore(layout)
    store.add("CSV 파서는 따옴표 이스케이프를 처리해야 한다", namespace="project", tags=["csv"])
    store.add("로그인 버그는 토큰 만료 때문", namespace="project", tags=["auth", "bug"])
    store.add("무관한 노트", namespace="scratch")

    assert len(store.query(namespace="project")) == 2
    assert len(store.query(tags=["bug"])) == 1
    assert store.query(tags=["auth", "bug"])[0].text.startswith("로그인")
    assert len(store.query(namespace="scratch")) == 1


def test_query_text_contains_and_since(layout: StateLayout):
    store = MemoryStore(layout)
    e1 = store.add("첫 메모", namespace="default")
    store.add("두번째 파서 메모", namespace="default")

    assert len(store.query(text_contains="파서")) == 1
    # since: 첫 항목 생성 이후로 필터하면 모두 포함(>=)
    assert len(store.query(since=e1.created_at)) == 2


def test_add_is_idempotent_by_content(layout: StateLayout):
    store = MemoryStore(layout)
    a = store.add("같은 내용", namespace="ns")
    b = store.add("같은 내용", namespace="ns")
    assert a.id == b.id
    assert len(store.all()) == 1


def test_recall_ranks_by_overlap(layout: StateLayout):
    store = MemoryStore(layout)
    store.add("CSV 파서 따옴표 이스케이프 규칙", namespace="project")
    store.add("완전히 무관한 날씨 이야기", namespace="project")

    hits = store.recall("CSV 파서 이스케이프 어떻게", top_k=1)
    assert len(hits) == 1
    assert "CSV" in hits[0].text


def test_recall_empty_when_no_overlap(layout: StateLayout):
    store = MemoryStore(layout)
    store.add("apple banana cherry", namespace="default")
    assert store.recall("xyzzy plugh", top_k=3) == []


def test_injector_formats_memory_block(layout: StateLayout):
    store = MemoryStore(layout)
    store.add("파서는 BOM을 제거한다", namespace="project")
    block = MemoryInjector(store).recall("파서 BOM 처리")
    assert block.startswith("<memory>")
    assert "BOM" in block

    # 회상 결과 없으면 빈 문자열
    assert MemoryInjector(store).recall("관계없는질의어") == ""
