"""SkillWriter — 추출된 스킬을 게이트를 거쳐 격리(proposed) 디렉토리에 기록한다.

자동 생성 스킬은 신뢰 불가로 취급한다:
  파싱 검증 → 안전성 스캔 → 이름/트리거 dedup → 'proposed'에 격리(자동 로드 안 됨).
활성(`./.superharness/skills`, 다음 로드 시 자동 적용)으로 올리려면 사람이 `promote`해야 한다.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from superharness.errors import SkillError
from superharness.skills.registry import SkillRegistry
from superharness.skills.skill import load_skill_text

# 보수적 deny-list — 1차 방어선(완전하지 않음). 비밀 노출/위험 명령을 거른다.
_UNSAFE_TOKENS = (
    "api_key",
    "apikey",
    "anthropic_api_key",
    "password",
    "secret",
    "exfiltrat",
    "rm -rf",
    "/etc/passwd",
    "base64 -d",
    "curl http",
)


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    REJECTED_INVALID = "rejected_invalid"
    REJECTED_UNSAFE = "rejected_unsafe"
    REJECTED_DUPLICATE = "rejected_duplicate"


class Proposal(BaseModel):
    status: ProposalStatus
    name: str | None = None
    path: str | None = None
    reason: str = ""


class SkillWriter:
    """추출 스킬의 게이트 + 격리/승격."""

    def __init__(self, active_dir: Path, proposed_dir: Path, registry: SkillRegistry) -> None:
        self.active_dir = Path(active_dir)        # SkillRegistry가 자동 로드하는 디렉토리
        self.proposed_dir = Path(proposed_dir)    # 격리 — 자동 로드되지 않음
        self.registry = registry                  # dedup 기준(현재 활성 스킬들)

    def propose(self, skill_md: str) -> Proposal:
        # 1) 파싱 검증 — 망가진 frontmatter 거부
        try:
            skill = load_skill_text(skill_md)
        except SkillError as exc:
            return Proposal(status=ProposalStatus.REJECTED_INVALID, reason=str(exc))

        # 2) 안전성 스캔 — 비밀/위험 토큰 거부 (프롬프트 인젝션·공급망 1차 방어)
        low = skill_md.lower()
        hit = next((t for t in _UNSAFE_TOKENS if t in low), None)
        if hit:
            return Proposal(
                status=ProposalStatus.REJECTED_UNSAFE,
                name=skill.name,
                reason=f"unsafe token: {hit!r}",
            )

        # 3) dedup — 이름 중복 또는 기존 스킬과 트리거 충돌
        if self.registry.get(skill.name) is not None:
            return Proposal(
                status=ProposalStatus.REJECTED_DUPLICATE,
                name=skill.name,
                reason="name already exists",
            )
        for trig in skill.frontmatter.triggers:
            if self.registry.detect(trig):
                return Proposal(
                    status=ProposalStatus.REJECTED_DUPLICATE,
                    name=skill.name,
                    reason=f"trigger collision: {trig!r}",
                )

        # 4) 격리 기록 — 자동 활성화하지 않는다
        self.proposed_dir.mkdir(parents=True, exist_ok=True)
        path = self.proposed_dir / f"{skill.name}.md"
        path.write_text(skill_md, encoding="utf-8")
        return Proposal(status=ProposalStatus.PROPOSED, name=skill.name, path=str(path))

    def list_proposed(self) -> list[str]:
        if not self.proposed_dir.is_dir():
            return []
        return sorted(p.stem for p in self.proposed_dir.glob("*.md"))

    def promote(self, name: str) -> Path:
        """격리된 스킬을 활성 디렉토리로 승격 → 다음 SkillRegistry.load()부터 적용."""
        src = self.proposed_dir / f"{name}.md"
        if not src.exists():
            raise SkillError(f"제안된 스킬이 없음: {name!r}")
        self.active_dir.mkdir(parents=True, exist_ok=True)
        dst = self.active_dir / f"{name}.md"
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        src.unlink()
        return dst
