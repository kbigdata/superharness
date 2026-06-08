"""SkillRegistry — builtin + 프로젝트/유저 스코프 스킬을 로드한다.

우선순위: 프로젝트(.superharness/skills) > 유저(~/.superharness/skills) > builtin
(같은 name이면 뒤가 override).
"""

from __future__ import annotations

from pathlib import Path

from superharness.logging import get_logger
from superharness.skills.injector import Activation, SkillInjector
from superharness.skills.keyword_detector import KeywordDetector, MatchedTrigger
from superharness.skills.skill import Skill, load_skill_file

log = get_logger("skills")

_BUILTIN_DIR = Path(__file__).parent / "builtin"


class SkillRegistry:
    """로드된 스킬 모음 + detector/injector 진입점."""

    def __init__(self, skills: list[Skill]) -> None:
        self._skills = {s.name: s for s in skills}
        self.detector = KeywordDetector(list(self._skills.values()))
        self.injector = SkillInjector(list(self._skills.values()))

    @property
    def skills(self) -> list[Skill]:
        return list(self._skills.values())

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def detect(self, prompt: str) -> list[MatchedTrigger]:
        return self.detector.detect(prompt)

    def activate(self, prompt: str) -> Activation:
        return self.injector.activate(self.detect(prompt))

    @classmethod
    def load(cls, *, extra_dirs: list[Path] | None = None) -> SkillRegistry:
        """builtin → 유저 → 프로젝트 → extra_dirs 순으로 로드 (뒤가 override)."""
        dirs: list[Path] = [_BUILTIN_DIR, Path.home() / ".superharness" / "skills",
                            Path.cwd() / ".superharness" / "skills"]
        if extra_dirs:
            dirs.extend(extra_dirs)
        by_name: dict[str, Skill] = {}
        for d in dirs:
            if not d.is_dir():
                continue
            for path in sorted(d.glob("*.md")):
                try:
                    skill = load_skill_file(path)
                    by_name[skill.name] = skill
                except Exception as exc:  # noqa: BLE001 - 한 파일 실패가 전체를 막지 않게
                    log.warning("스킬 로드 실패 %s: %s", path, exc)
        return cls(list(by_name.values()))
