"""스킬 레이어 — 키워드→스킬 활성화."""

from __future__ import annotations

from superharness.skills.injector import Activation, SkillInjector
from superharness.skills.keyword_detector import KeywordDetector, MatchedTrigger
from superharness.skills.registry import SkillRegistry
from superharness.skills.similarity import (
    LexicalSimilarity,
    Similarity,
    SimilarityResult,
)
from superharness.skills.skill import (
    Skill,
    SkillFrontmatter,
    load_skill_file,
    load_skill_text,
)
from superharness.skills.versions import SkillVersionStore, VersionEntry
from superharness.skills.writer import Proposal, ProposalStatus, SkillWriter

__all__ = [
    "Skill",
    "SkillFrontmatter",
    "load_skill_file",
    "load_skill_text",
    "KeywordDetector",
    "MatchedTrigger",
    "SkillInjector",
    "Activation",
    "SkillRegistry",
    "SkillWriter",
    "Proposal",
    "ProposalStatus",
    "SkillVersionStore",
    "VersionEntry",
    "Similarity",
    "SimilarityResult",
    "LexicalSimilarity",
]
