from __future__ import annotations

import pytest
from pydantic import ValidationError

from superharness.errors import PathViolation, StateError
from superharness.state.paths import as_read_path, as_write_path


def test_write_read_roundtrip(artifacts):
    desc = artifacts.write("result", "hello world", producer="test")
    assert desc.kind == "result"
    assert desc.size_bytes == len("hello world")
    assert artifacts.read(desc) == "hello world"


def test_hash_tamper_detected(artifacts, layout):
    desc = artifacts.write("result", "original", producer="test")
    # 디스크 내용을 변조 → read 시 해시 불일치
    (layout.root / desc.path).write_text("tampered")
    with pytest.raises(StateError):
        artifacts.read(desc)


def test_branded_path_blocks_traversal(layout):
    with pytest.raises(PathViolation):
        as_write_path(layout.root, "../../etc/passwd")
    with pytest.raises(PathViolation):
        as_read_path(layout.root, "../escape")


def test_descriptor_is_frozen(artifacts):
    desc = artifacts.write("note", "x", producer="t")
    with pytest.raises(ValidationError):
        desc.kind = "other"  # type: ignore[misc]
