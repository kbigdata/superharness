"""라이브 Anthropic API 테스트 — 실제 1콜로 AnthropicProvider end-to-end 검증.

기본은 자동 skip. 실행하려면:
    uv pip install -e ".[dev,anthropic]"
    ANTHROPIC_API_KEY=sk-ant-... uv run pytest -m live
저비용을 위해 LOW 티어(haiku) + 작은 max_tokens만 호출한다.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

from superharness.config import TierModelMap
from superharness.providers.anthropic_provider import AnthropicProvider
from superharness.providers.base import CompletionRequest, Message, Tier

pytestmark = pytest.mark.live

_HAS_ANTHROPIC = importlib.util.find_spec("anthropic") is not None
_HAS_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))


@pytest.mark.skipif(not _HAS_ANTHROPIC, reason="anthropic extra 미설치 (.[dev,anthropic])")
@pytest.mark.skipif(not _HAS_KEY, reason="ANTHROPIC_API_KEY 미설정 — 라이브 호출 생략")
async def test_live_haiku_completion():
    """실제 Haiku 호출: 비어있지 않은 응답 + 티어 라우팅 + 사용량 집계 확인."""
    model = TierModelMap().resolve(Tier.LOW)          # claude-haiku-4-5
    provider = AnthropicProvider()                     # ANTHROPIC_API_KEY를 환경에서 읽음
    res = await provider.complete(
        CompletionRequest(
            model=model,
            messages=[Message(role="user", content="Reply with exactly one word: pong")],
            max_tokens=16,
        )
    )
    assert res.text.strip()                            # 비어있지 않은 응답
    assert res.model.startswith("claude-haiku-4-5")     # LOW 티어 → haiku 라우팅
    assert res.usage.input_tokens > 0                   # 사용량 집계
    assert res.usage.output_tokens > 0


@pytest.mark.skipif(not _HAS_ANTHROPIC, reason="anthropic extra 미설치 (.[dev,anthropic])")
@pytest.mark.skipif(not _HAS_KEY, reason="ANTHROPIC_API_KEY 미설정 — 라이브 호출 생략")
async def test_live_opus_adaptive_thinking():
    """HIGH 티어(opus) + adaptive thinking + effort 경로가 400 없이 동작하는지 확인."""
    model = TierModelMap().resolve(Tier.HIGH)          # claude-opus-4-8
    provider = AnthropicProvider()
    res = await provider.complete(
        CompletionRequest(
            model=model,
            messages=[Message(role="user", content="What is 2+2? Reply with the number only.")],
            max_tokens=64,
            thinking=True,
            effort="low",
        )
    )
    assert res.text.strip()
    assert res.model.startswith("claude-opus-4-8")
