"""MockProvider — 네트워크 없는 결정적 프로바이더. 기본값이며 오프라인 테스트의 핵심.

규칙 기반 응답 + 호출 기록 + resolved model 에코(티어 라우팅 검증용).
"""

from __future__ import annotations

from collections.abc import Callable

from superharness.providers.base import CompletionRequest, CompletionResult, Usage


class MockProvider:
    """결정적 가짜 프로바이더.

    rules: (마지막 user 메시지에 포함되면 매칭되는 부분문자열) -> 응답 텍스트.
    매칭이 없으면 resolved model을 에코하는 기본 응답을 돌려준다.
    """

    name = "mock"

    def __init__(self, rules: dict[str, str] | None = None) -> None:
        self._rules: list[tuple[str, str]] = list((rules or {}).items())
        self._fns: list[tuple[Callable[[CompletionRequest], bool], str]] = []
        self.calls: list[CompletionRequest] = []

    def when(self, substring: str, respond: str) -> MockProvider:
        """부분문자열 매칭 규칙 추가 (체이닝 가능)."""
        self._rules.append((substring.lower(), respond))
        return self

    def when_fn(
        self, predicate: Callable[[CompletionRequest], bool], respond: str
    ) -> MockProvider:
        """임의 술어 기반 규칙 추가."""
        self._fns.append((predicate, respond))
        return self

    async def complete(self, req: CompletionRequest) -> CompletionResult:
        self.calls.append(req)
        last_user = next(
            (m.content for m in reversed(req.messages) if m.role == "user"), ""
        )
        haystack = last_user.lower()

        text: str | None = None
        for predicate, respond in self._fns:
            if predicate(req):
                text = respond
                break
        if text is None:
            for needle, respond in self._rules:
                if needle in haystack:
                    text = respond
                    break
        if text is None:
            text = f"[mock:{req.model}] {last_user}".strip()

        return CompletionResult(
            text=text,
            model=req.model,
            usage=Usage(input_tokens=len(haystack.split()), output_tokens=len(text.split())),
        )
