from __future__ import annotations

from superharness.providers.base import CompletionRequest, Message
from superharness.providers.mock_provider import MockProvider


async def test_rule_match():
    prov = MockProvider().when("weather", "sunny")
    res = await prov.complete(
        CompletionRequest(model="m", messages=[Message(role="user", content="the weather?")])
    )
    assert res.text == "sunny"


async def test_default_echoes_model_for_routing_assertions():
    prov = MockProvider()
    res = await prov.complete(
        CompletionRequest(model="claude-opus-4-8", messages=[Message(role="user", content="hi")])
    )
    assert "claude-opus-4-8" in res.text


async def test_records_calls():
    prov = MockProvider()
    await prov.complete(CompletionRequest(model="m", messages=[Message(role="user", content="a")]))
    await prov.complete(CompletionRequest(model="m", messages=[Message(role="user", content="b")]))
    assert len(prov.calls) == 2
