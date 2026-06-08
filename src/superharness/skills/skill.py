"""Skill 모델 + frontmatter 파싱.

스킬은 YAML frontmatter(메타) + 마크다운 본문(주입 지시문)으로 구성된 워크플로 단위다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from superharness.errors import SkillError

Mode = Literal["team", "ralph", "autopilot", "ultrawork", "plain"]


class SkillFrontmatter(BaseModel):
    """스킬 메타데이터."""

    name: str
    description: str = ""
    triggers: list[str] = Field(default_factory=list)
    pipeline: list[str] | None = None
    next_skill: str | None = None
    mode: Mode = "plain"


class Skill(BaseModel):
    """frontmatter + 본문."""

    frontmatter: SkillFrontmatter
    body: str

    @property
    def name(self) -> str:
        return self.frontmatter.name


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise SkillError("스킬 파일은 '---' frontmatter로 시작해야 합니다.")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillError("frontmatter 종료 구분자 '---'를 찾을 수 없습니다.")
    meta = yaml.safe_load(parts[1]) or {}
    if not isinstance(meta, dict):
        raise SkillError("frontmatter는 매핑(dict)이어야 합니다.")
    return meta, parts[2].strip()


def load_skill_text(text: str) -> Skill:
    meta, body = _split_frontmatter(text)
    return Skill(frontmatter=SkillFrontmatter(**meta), body=body)


def load_skill_file(path: str | Path) -> Skill:
    p = Path(path)
    try:
        return load_skill_text(p.read_text(encoding="utf-8"))
    except SkillError as exc:
        raise SkillError(f"{p}: {exc}") from exc
