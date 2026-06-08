"""AnthropicProvider — 실제 Claude 백엔드.

claude-api 레퍼런스 기준 핵심 주의사항(MEDIUM/HIGH 티어 = sonnet-4-6/opus-4-8):
- thinking은 `{"type": "adaptive"}`, effort는 `output_config={"effort": ...}`.
- `temperature`/`top_p`/`budget_tokens`는 절대 전송 금지 (해당 모델에서 400).
- effort는 opus/sonnet-4-6에서만 유효 (haiku-4-5에선 미전송).
- 큰 max_tokens는 스트리밍으로 보내 HTTP 타임아웃을 피한다.
`anthropic` import는 lazy — mock 전용 설치에서는 의존성이 없어도 된다.
"""

from __future__ import annotations

from typing import Any

from superharness.errors import ProviderError, ProviderNotInstalled
from superharness.providers.base import CompletionRequest, CompletionResult, Usage

# effort/adaptive-thinking을 지원하는 모델 (claude-api 레퍼런스 기준)
_EFFORT_MODELS = ("claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6")
# 비-스트리밍이 안전한 max_tokens 상한
_STREAM_THRESHOLD = 16000


class AnthropicProvider:
    """Anthropic AsyncAnthropic 래퍼. 기본 client는 ANTHROPIC_API_KEY를 환경에서 읽는다."""

    name = "anthropic"

    def __init__(self, client: Any = None) -> None:
        if client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - 의존성 부재 경로
                raise ProviderNotInstalled(
                    "anthropic 프로바이더는 `pip install 'superharness[anthropic]'` 가 필요합니다."
                ) from exc
            client = anthropic.AsyncAnthropic()
        self._client: Any = client

    def _supports_effort(self, model: str) -> bool:
        return model in _EFFORT_MODELS

    def _build_kwargs(self, req: CompletionRequest) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages
                         if m.role != "system"],
        }
        if req.system:
            kwargs["system"] = req.system
        if req.thinking and self._supports_effort(req.model):
            kwargs["thinking"] = {"type": "adaptive"}
            kwargs["output_config"] = {"effort": req.effort or "high"}
        # temperature/top_p/budget_tokens 는 의도적으로 전송하지 않는다.
        return kwargs

    async def complete(self, req: CompletionRequest) -> CompletionResult:
        kwargs = self._build_kwargs(req)
        try:
            if req.max_tokens > _STREAM_THRESHOLD:
                async with self._client.messages.stream(**kwargs) as stream:
                    message = await stream.get_final_message()
            else:
                message = await self._client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - SDK 예외를 단일 타입으로 래핑
            raise ProviderError(f"anthropic 호출 실패: {exc}") from exc

        text = next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")
        usage = getattr(message, "usage", None)
        return CompletionResult(
            text=text,
            model=getattr(message, "model", req.model),
            usage=Usage(
                input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
                output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            ),
        )
