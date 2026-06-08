from __future__ import annotations

from pathlib import Path

import pytest

from superharness.agents.registry import AgentRegistry
from superharness.config import Settings, TierModelMap
from superharness.providers.mock_provider import MockProvider
from superharness.skills.registry import SkillRegistry
from superharness.state.artifacts import ArtifactStore
from superharness.state.paths import StateLayout
from superharness.state.store import StateStore


@pytest.fixture
def layout(tmp_path: Path) -> StateLayout:
    return StateLayout(tmp_path / ".superharness").init()


@pytest.fixture
def artifacts(layout: StateLayout) -> ArtifactStore:
    return ArtifactStore(layout)


@pytest.fixture
def store(layout: StateLayout) -> StateStore:
    return StateStore(layout)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        provider="mock",
        state_dir=str(tmp_path / ".superharness"),
        max_concurrency=4,
        max_iterations=5,
        tiers=TierModelMap(),
    )


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def agents() -> AgentRegistry:
    return AgentRegistry.default()


@pytest.fixture
def skills() -> SkillRegistry:
    return SkillRegistry.load()
