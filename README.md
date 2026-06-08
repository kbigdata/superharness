# 슈퍼하네스 — 범용 멀티에이전트 오케스트레이션 하네스

멀티에이전트 오케스트레이션의 핵심 패턴을
**프레임워크 중립 Python 코어**로 구현한 동작하는 MVP. Claude Code 플러그인이 아니라,
여러 LLM 백엔드를 추상화하는 독립형 라이브러리/CLI다.

## 무엇을 구현하나 (4대 핵심 패턴)

| 패턴 | 구현 |
|---|---|
| ① 키워드→스킬 활성화 | `KeywordDetector` + `SkillInjector` (키워드 감지 → 스킬 주입의 in-process 구현) |
| ② 멀티에이전트 오케스트레이션 | `Orchestrator`(asyncio fan-out) + `TeamPipeline`(plan→exec→verify→fix) |
| ③ 지속/검증 루프 (Ralph) | `RalphLoop` + `PersistentMode`(STOP 차단) |
| ④ 상태/아티팩트 + 티어 라우팅 | `StateStore`(control) / `ArtifactStore`+`ArtifactDescriptor`(data) / `TierModelMap` |

## 설치

```bash
pip install -e ".[dev]"          # 코어 + 개발 도구 (오프라인)
pip install -e ".[dev,anthropic]"  # 실제 Claude 백엔드까지
```

## 빠른 시작 (API 키 불필요 — 기본 mock 프로바이더)

```bash
superharness --help
superharness ask "hello"                       # 단일 완성 (오프라인)
superharness state init                        # .superharness 상태 트리 생성 + 샘플 아티팩트
superharness skills list                       # 로드된 스킬/트리거
superharness skills detect "ultrawork: refactor, don't stop until done"
superharness agents run executor "write a CSV parser"
superharness team "build a CSV parser"
superharness demo                              # E2E: detect→inject→pipeline→ralph→artifacts
```

## 실제 Claude로 전환

```bash
SUPERHARNESS_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... superharness ask "hello"
```

프로바이더 레지스트리(`superharness.providers.get_provider`)가 유일한 교체 지점이다.
티어→모델: `low→claude-haiku-4-5`, `medium→claude-sonnet-4-6`, `high→claude-opus-4-8`.

## 아키텍처

- **control plane / data plane 분리**: 컨트롤(큐·세션·project-memory)은 작게, 데이터
  (plan/spec/result/trace)는 디스크 아티팩트로 두고 `ArtifactDescriptor`(kind, path,
  content_hash, producer, created_at)로 참조.
- **브랜디드 경로**: `ReadPath`/`WritePath`(NewType + 검증 생성자)로 정적 구분 + traversal 차단.
- **도메인×티어 에이전트 매트릭스**: `AgentRegistry`는 데이터 주도 — 새 에이전트는 매트릭스 편집.
- **동시성**: asyncio(+anyio). provider I/O 바운드 fan-out, `CapacityLimiter`로 제한,
  `TaskList`는 `asyncio.Lock`으로 atomic claim/complete/fail.

## 테스트

```bash
pytest -q          # 전 테스트 오프라인(mock) — 네트워크/키 불필요
ruff check .
mypy src
```

## 디렉토리

```
src/superharness/
  providers/   base(Provider Protocol, Tier) · mock · anthropic · 레지스트리
  skills/      skill · registry · keyword_detector · injector · builtin/*.md
  agents/      agent(도메인×티어) · registry(매트릭스)
  orchestration/ task · orchestrator · pipeline(Team) · ralph
  hooks/       events · bus(+ persistent-mode STOP 가드)
  state/       paths(브랜디드) · descriptor · artifacts(data) · store(control)
  cli.py       Typer: ask / state / skills / agents / team / demo
```

라이선스: MIT.
