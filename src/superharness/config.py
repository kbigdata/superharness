"""설정 — pydantic-settings 기반. 기본 → 환경변수(SUPERHARNESS_*) → CLI override.

티어→모델 매핑은 여기서 중앙화한다 (claude-api 레퍼런스 기준 모델 id).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from superharness.providers.base import Tier


class TierModelMap(BaseSettings):
    """티어→모델 id 매핑. 환경변수 SUPERHARNESS_TIER_{LOW,MEDIUM,HIGH}로 override."""

    model_config = SettingsConfigDict(env_prefix="SUPERHARNESS_TIER_")

    low: str = "claude-haiku-4-5"
    medium: str = "claude-sonnet-4-6"
    high: str = "claude-opus-4-8"

    def resolve(self, tier: Tier) -> str:
        return {Tier.LOW: self.low, Tier.MEDIUM: self.medium, Tier.HIGH: self.high}[tier]


class Settings(BaseSettings):
    """하네스 전역 설정."""

    model_config = SettingsConfigDict(env_prefix="SUPERHARNESS_", extra="ignore")

    provider: str = "mock"
    state_dir: str = "./.superharness"
    parallel_execution: bool = True
    max_concurrency: int = 4
    max_iterations: int = 10

    tiers: TierModelMap = Field(default_factory=TierModelMap)


def load_settings(**overrides: object) -> Settings:
    """Settings를 로드하고 명시적 override를 적용한다 (CLI 플래그용)."""
    settings = Settings()
    if overrides:
        clean = {k: v for k, v in overrides.items() if v is not None}
        if clean:
            settings = settings.model_copy(update=clean)
    return settings
