"""프로바이더 레지스트리 — 이름으로 백엔드를 교체하는 단일 지점."""

from __future__ import annotations

from superharness.errors import ConfigError
from superharness.providers.base import (
    CompletionRequest,
    CompletionResult,
    Message,
    Provider,
    Tier,
    Usage,
)
from superharness.providers.mock_provider import MockProvider

__all__ = [
    "Provider",
    "Tier",
    "Message",
    "CompletionRequest",
    "CompletionResult",
    "Usage",
    "MockProvider",
    "get_provider",
]


def get_provider(name: str, **kwargs: object) -> Provider:
    """이름으로 프로바이더 인스턴스를 만든다.

    - "mock"     → MockProvider (오프라인 기본값)
    - "anthropic"→ AnthropicProvider (lazy import; anthropic extra 필요)
    """
    key = name.lower()
    if key == "mock":
        return MockProvider()
    if key == "anthropic":
        from superharness.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(**kwargs)
    raise ConfigError(f"알 수 없는 프로바이더: {name!r} (지원: mock, anthropic)")
