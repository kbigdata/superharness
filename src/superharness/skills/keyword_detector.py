"""KeywordDetector — 자연어 프롬프트에서 트리거 키워드를 찾아 스킬을 매칭한다.

키워드 감지의 in-process 구현. word-boundary 매칭 + longest-match 우선.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from superharness.skills.skill import Skill


class MatchedTrigger(BaseModel):
    keyword: str
    skill_name: str
    start: int
    end: int


class KeywordDetector:
    """스킬 트리거를 컴파일해 두고 프롬프트에 대해 매칭한다."""

    def __init__(self, skills: list[Skill]) -> None:
        # (trigger_lower, compiled_pattern, skill_name) — 긴 트리거 우선
        entries: list[tuple[str, re.Pattern[str], str]] = []
        for skill in skills:
            for trig in skill.frontmatter.triggers:
                t = trig.lower().strip()
                if not t:
                    continue
                pattern = re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE)
                entries.append((t, pattern, skill.name))
        entries.sort(key=lambda e: len(e[0]), reverse=True)
        self._entries = entries

    def detect(self, prompt: str) -> list[MatchedTrigger]:
        """매칭된 트리거를 위치 순으로, 스킬당 1회만 반환한다."""
        matches: list[MatchedTrigger] = []
        seen_skills: set[str] = set()
        for keyword, pattern, skill_name in self._entries:
            if skill_name in seen_skills:
                continue
            m = pattern.search(prompt)
            if m:
                seen_skills.add(skill_name)
                matches.append(
                    MatchedTrigger(
                        keyword=keyword,
                        skill_name=skill_name,
                        start=m.start(),
                        end=m.end(),
                    )
                )
        matches.sort(key=lambda x: x.start)
        return matches
