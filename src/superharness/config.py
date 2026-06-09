"""설정 — pydantic-settings 기반. 기본 → 환경변수(SUPERHARNESS_*) → CLI override.

티어→모델 매핑은 여기서 중앙화한다 (claude-api 레퍼런스 기준 모델 id).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from superharness.providers.base import Tier


def derive_project_id(cwd: str | Path | None = None) -> str:
    """cwd 경로의 안정 해시로 project-id를 파생한다 (12자, 결정적)."""
    base = str(Path(cwd).resolve()) if cwd is not None else str(Path.cwd().resolve())
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]


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
    # 멀티프로젝트 격리: state_root가 설정되면 effective state_dir = {state_root}/{project_id}.
    # state_root 미설정 시 기존 동작(state_dir 그대로) — 하위호환.
    state_root: str | None = None
    project_id: str | None = None
    parallel_execution: bool = True
    max_concurrency: int = 4
    max_iterations: int = 10

    tiers: TierModelMap = Field(default_factory=TierModelMap)

    @model_validator(mode="after")
    def _apply_project_isolation(self) -> Settings:
        """state_root가 있으면 project_id별 디렉토리로 state_dir을 파생한다."""
        if self.state_root:
            pid = self.project_id or derive_project_id()
            self.project_id = pid
            self.state_dir = str(Path(self.state_root) / pid)
        return self


def load_settings(**overrides: object) -> Settings:
    """Settings를 로드하고 명시적 override를 적용한다 (CLI 플래그용)."""
    settings = Settings()
    if overrides:
        clean = {k: v for k, v in overrides.items() if v is not None}
        if clean:
            settings = settings.model_copy(update=clean)
    return settings
