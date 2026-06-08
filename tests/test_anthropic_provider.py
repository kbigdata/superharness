"""AnthropicProvider 요청 셰이핑 검증 — fake client 사용(네트워크/anthropic 의존 불필요).

load-bearing 규칙을 회귀 방지: adaptive thinking + output_config.effort,
temperature/top_p/budget_tokens 미전송, haiku는 effort 생략, 큰 max_tokens는 스트리밍, 에러 래핑.
"""

from __future__ import annotations

import pytest

from superharness.errors import ProviderError
from superharness.providers.anthropic_provider import AnthropicProvider
from superharness.providers.base import CompletionRequest, Message


class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Usage:
    input_tokens = 1
    output_tokens = 2


class _Resp:
    def __init__(self, text: str, model: str) -> None:
        self.content = [_Block(text)]
        self.model = model
        self.usage = _Usage()


class _StreamCtx:
    def __init__(self, model: str) -> None:
        self._model = model

    async def __aenter__(self):
        model = self._model

        class _S:
            async def get_final_message(self):
                return _Resp("streamed", model)

        return _S()

    async def __aexit__(self, *exc):
        return False


class _Messages:
    def __init__(self, captured: dict, raise_exc: Exception | None = None) -> None:
        self.captured = captured
        self.raise_exc = raise_exc

    async def create(self, **kw):
        self.captured.update(kw)
        if self.raise_exc:
            raise self.raise_exc
        return _Resp("created", kw["model"])

    def stream(self, **kw):
        self.captured.update(kw)
        self.captured["_streamed"] = True
        return _StreamCtx(kw["model"])


class _Client:
    def __init__(self, captured: dict, raise_exc: Exception | None = None) -> None:
        self.messages = _Messages(captured, raise_exc)


async def test_opus_sends_adaptive_thinking_and_effort_only():
    cap: dict = {}
    prov = AnthropicProvider(client=_Client(cap))
    req = CompletionRequest(
        model="claude-opus-4-8", system="s",
        messages=[Message(role="user", content="hi")], thinking=True, effort="high",
    )
    res = await prov.complete(req)
    assert res.text == "created"
    assert cap["thinking"] == {"type": "adaptive"}
    assert cap["output_config"] == {"effort": "high"}
    # 금지 파라미터는 절대 전송되지 않는다 (해당 모델에서 400)
    assert "temperature" not in cap
    assert "top_p" not in cap
    assert "budget_tokens" not in cap
    # system은 분리, messages에는 system 롤이 제외된다
    assert cap["system"] == "s"
    assert cap["messages"] == [{"role": "user", "content": "hi"}]


async def test_haiku_omits_thinking_and_effort():
    cap: dict = {}
    prov = AnthropicProvider(client=_Client(cap))
    await prov.complete(
        CompletionRequest(
            model="claude-haiku-4-5",
            messages=[Message(role="user", content="x")], thinking=True, effort="high",
        )
    )
    assert "thinking" not in cap
    assert "output_config" not in cap


async def test_large_max_tokens_uses_streaming():
    cap: dict = {}
    prov = AnthropicProvider(client=_Client(cap))
    res = await prov.complete(
        CompletionRequest(
            model="claude-sonnet-4-6",
            messages=[Message(role="user", content="x")], max_tokens=20000,
        )
    )
    assert cap.get("_streamed") is True
    assert res.text == "streamed"


async def test_small_max_tokens_uses_create():
    cap: dict = {}
    prov = AnthropicProvider(client=_Client(cap))
    res = await prov.complete(
        CompletionRequest(
            model="claude-sonnet-4-6",
            messages=[Message(role="user", content="x")], max_tokens=1000,
        )
    )
    assert cap.get("_streamed") is None
    assert res.text == "created"


async def test_sdk_error_is_wrapped_as_provider_error():
    prov = AnthropicProvider(client=_Client({}, raise_exc=RuntimeError("boom")))
    with pytest.raises(ProviderError):
        await prov.complete(
            CompletionRequest(
                model="claude-opus-4-8", messages=[Message(role="user", content="x")]
            )
        )
