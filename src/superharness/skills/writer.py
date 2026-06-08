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
from superharness.skills.versions import SkillVersionStore, VersionEntry

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

    def __init__(
        self,
        active_dir: Path,
        proposed_dir: Path,
        registry: SkillRegistry,
        versions: SkillVersionStore | None = None,
    ) -> None:
        self.active_dir = Path(active_dir)        # SkillRegistry가 자동 로드하는 디렉토리
        self.proposed_dir = Path(proposed_dir)    # 격리 — 자동 로드되지 않음
        self.registry = registry                  # dedup 기준(현재 활성 스킬들)
        self.versions = versions                  # 활성 스킬 버전 이력(선택)

    def propose(self, skill_md: str, *, refine: bool = False) -> Proposal:
        """추출 스킬을 게이트 후 격리한다. refine=True면 기존 스킬 개선안이므로 dedup을 건너뛴다."""
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

        # 3) dedup — 신규 스킬만(refine은 동일 name 개선이므로 건너뜀)
        if not refine:
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
        """격리된 스킬을 활성 디렉토리로 승격 → 다음 SkillRegistry.load()부터 적용. 버전 기록."""
        src = self.proposed_dir / f"{name}.md"
        if not src.exists():
            raise SkillError(f"제안된 스킬이 없음: {name!r}")
        content = src.read_text(encoding="utf-8")
        self.active_dir.mkdir(parents=True, exist_ok=True)
        dst = self.active_dir / f"{name}.md"
        dst.write_text(content, encoding="utf-8")
        src.unlink()
        if self.versions is not None:
            self.versions.record(name, content, "promoted")
        return dst

    def history(self, name: str) -> list[VersionEntry]:
        """활성 스킬의 버전 이력(최신 우선)."""
        return self.versions.history(name) if self.versions is not None else []

    def rollback(self, name: str, version: int) -> Path:
        """특정 버전 내용을 활성 디렉토리로 복원하고 새 버전으로 기록한다."""
        if self.versions is None:
            raise SkillError("버전 스토어가 없어 롤백할 수 없습니다")
        content = self.versions.get(name, version)
        self.active_dir.mkdir(parents=True, exist_ok=True)
        dst = self.active_dir / f"{name}.md"
        dst.write_text(content, encoding="utf-8")
        self.versions.record(name, content, "rolledback")
        return dst
