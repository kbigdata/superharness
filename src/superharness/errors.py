"""하네스 예외 계층."""

from __future__ import annotations


class HarnessError(Exception):
    """모든 하네스 예외의 베이스."""


class ConfigError(HarnessError):
    """설정 로드/검증 실패."""


class ProviderError(HarnessError):
    """LLM 프로바이더 호출 실패."""


class ProviderNotInstalled(ProviderError):
    """프로바이더의 선택적 의존성이 설치되지 않음 (예: anthropic extra)."""


class SkillError(HarnessError):
    """스킬 로드/파싱 실패."""


class AgentError(HarnessError):
    """에이전트 디스패치/실행 실패."""


class StateError(HarnessError):
    """상태/아티팩트 저장소 오류 (경로 위반, 해시 불일치 등)."""


class PathViolation(StateError):
    """브랜디드 경로가 상태 디렉토리를 벗어나거나 traversal을 시도함."""


class CodebaseError(HarnessError):
    """코드베이스 읽기 도구 오류 (바이너리/누락 파일 등)."""
