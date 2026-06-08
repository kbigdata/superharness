"""프로바이더 레지스트리 — get_provider 분기/에러 경로."""

from __future__ import annotations

import importlib.util

import pytest

from superharness.errors import ConfigError, ProviderNotInstalled
from superharness.providers import get_provider


def test_get_provider_mock():
    assert get_provider("mock").name == "mock"


def test_get_provider_unknown_raises():
    with pytest.raises(ConfigError):
        get_provider("nope")


@pytest.mark.skipif(
    importlib.util.find_spec("anthropic") is not None,
    reason="anthropic extra 설치됨 — not-installed 경로 검증 불가",
)
def test_get_provider_anthropic_not_installed():
    with pytest.raises(ProviderNotInstalled):
        get_provider("anthropic")
