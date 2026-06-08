"""AgentRegistry — 도메인×티어 에이전트 매트릭스 (data-driven).

새 에이전트 추가는 매트릭스 데이터 편집이지 새 클래스가 아니다 (도메인×티어 구조).
"""

from __future__ import annotations

from superharness.agents.agent import Agent, AgentSpec
from superharness.errors import AgentError
from superharness.providers.base import Tier

# 기본 매트릭스: (domain, tier, system_prompt). report §4 도메인을 미러링.
_DEFAULT_MATRIX: list[tuple[str, Tier, str]] = [
    ("architect", Tier.LOW, "당신은 빠른 구조 분석가입니다. 핵심만 간결히 분석하세요."),
    ("architect", Tier.MEDIUM, "당신은 시스템 아키텍트입니다. 설계 트레이드오프를 분석하세요."),
    ("architect", Tier.HIGH, "당신은 수석 아키텍트입니다. 깊이 있는 설계와 위험을 분석하세요."),
    ("executor", Tier.LOW, "당신은 단순 실행자입니다. 지시를 그대로 빠르게 수행하세요."),
    ("executor", Tier.MEDIUM, "당신은 실행 엔지니어입니다. 태스크를 구현하세요."),
    ("executor", Tier.HIGH, "당신은 시니어 실행 엔지니어입니다. 복잡한 구현을 완수하세요."),
    ("explore", Tier.LOW, "당신은 탐색 에이전트입니다. 관련 정보를 찾으세요."),
    ("explore", Tier.HIGH, "당신은 심층 탐색 에이전트입니다. 광범위하게 조사하세요."),
    ("designer", Tier.MEDIUM, "당신은 프론트엔드 디자이너입니다. UI를 설계하세요."),
    ("planner", Tier.HIGH, "당신은 기획자입니다. 목표를 실행 가능한 태스크 목록으로 분해하세요."),
    ("critic", Tier.HIGH, "당신은 비평가입니다. 결과의 결함을 비판적으로 검토하세요."),
    ("qa-tester", Tier.MEDIUM, "당신은 QA 테스터입니다. 산출물이 목표를 만족하는지 검증하세요."),
    ("security-reviewer", Tier.HIGH, "당신은 보안 리뷰어입니다. 취약점을 점검하세요."),
]


def _spec_name(domain: str, tier: Tier) -> str:
    return domain if tier == Tier.MEDIUM else f"{domain}-{tier.value}"


class AgentRegistry:
    def __init__(self, specs: list[AgentSpec]) -> None:
        self._by_name: dict[str, AgentSpec] = {s.name: s for s in specs}
        self._by_domain_tier: dict[tuple[str, Tier], AgentSpec] = {
            (s.domain, s.tier): s for s in specs
        }

    @classmethod
    def default(cls) -> AgentRegistry:
        specs = [
            AgentSpec(domain=d, tier=t, name=_spec_name(d, t), system_prompt=p)
            for d, t, p in _DEFAULT_MATRIX
        ]
        return cls(specs)

    @property
    def specs(self) -> list[AgentSpec]:
        return list(self._by_name.values())

    def get(self, domain: str, tier: Tier) -> Agent:
        spec = self._by_domain_tier.get((domain, tier))
        if spec is None:
            # 같은 도메인의 인접 티어로 폴백
            for fallback in (Tier.MEDIUM, Tier.HIGH, Tier.LOW):
                spec = self._by_domain_tier.get((domain, fallback))
                if spec:
                    break
        if spec is None:
            raise AgentError(f"에이전트를 찾을 수 없음: domain={domain!r} tier={tier.value}")
        return Agent(spec)

    def get_by_name(self, name: str) -> Agent:
        spec = self._by_name.get(name)
        if spec is None:
            raise AgentError(f"에이전트를 찾을 수 없음: {name!r}")
        return Agent(spec)
