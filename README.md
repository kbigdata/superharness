# 슈퍼하네스 (superharness)

> 범용 멀티에이전트 오케스트레이션 하네스 — 프레임워크 중립 Python 코어

[![CI](https://github.com/kbigdata/superharness/actions/workflows/ci.yml/badge.svg)](https://github.com/kbigdata/superharness/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Built with uv](https://img.shields.io/badge/built%20with-uv-261230)
![Coverage](https://img.shields.io/badge/coverage-95%25-success)

멀티에이전트 오케스트레이션의 핵심 패턴(키워드→스킬 활성화 · 병렬 협업 · 지속/검증 루프 ·
상태/티어 라우팅)을 **하나의 작고 실행 가능한 Python 코어**로 구현했다. Claude Code 플러그인이
아니라, 여러 LLM 백엔드를 추상화하는 **독립형 라이브러리 + CLI**다.

- **기본값이 오프라인** — API 키 없이 `mock` 프로바이더로 전 기능이 돌아간다(테스트·데모 포함).
- **한 줄로 실 Claude 전환** — `SUPERHARNESS_PROVIDER=anthropic` 만 바꾸면 된다.
- **프레임워크 중립** — `Provider` Protocol 하나로 Anthropic/Mock/커스텀 백엔드를 교체.
- **확장은 데이터 편집** — 스킬은 마크다운, 에이전트는 매트릭스 한 줄로 추가.

---

## 목차

- [무엇을 구현하나](#무엇을-구현하나-4대-핵심-패턴)
- [동작 원리](#동작-원리-demo-한-줄의-흐름)
- [요구 사항 · 설치](#요구-사항--설치)
- [빠른 시작](#빠른-시작-api-키-불필요)
- [오케스트레이션 개념](#오케스트레이션-개념)
- [라이브러리로 임베드](#라이브러리로-임베드)
- [실제 Claude로 전환](#실제-claude로-전환)
- [설정(환경변수)](#설정-환경변수)
- [테스트 · 품질](#테스트--품질)
- [프로젝트 구조](#프로젝트-구조)
- [새 프로젝트에서 재사용](#새-프로젝트에서-재사용)
- [상태 · 로드맵](#상태--로드맵)

---

## 무엇을 구현하나 (4대 핵심 패턴)

| 패턴 | 무엇을 하나 | 구현 |
|---|---|---|
| ① **키워드→스킬 활성화** | 프롬프트의 트리거 단어를 감지해 워크플로(스킬)와 실행 모드를 주입 | `KeywordDetector` + `SkillInjector` |
| ② **멀티에이전트 오케스트레이션** | 공유 태스크 리스트를 도메인×티어 에이전트가 병렬 처리 | `Orchestrator`(asyncio fan-out) + `TeamPipeline` |
| ③ **지속/검증 루프 (Ralph)** | verify→fix를 목표 검증 완료까지 반복(부분 완료로 끝나지 않음) | `RalphLoop` + `PersistentMode`(STOP 차단) |
| ④ **상태/아티팩트 + 티어 라우팅** | control/data plane 분리, 해시 주소 아티팩트, 난이도→모델 매핑 | `StateStore` / `ArtifactStore` / `TierModelMap` |

---

## 동작 원리 (`demo` 한 줄의 흐름)

```
프롬프트  "ultrawork: build a CSV parser, don't stop until tests pass"
   │
   ▼  ① 키워드→스킬
[KeywordDetector] 트리거 감지 → ultrawork, "don't stop"
[SkillInjector]   스킬 본문 주입 + 모드 결정(ralph)         ← 가장 강한 모드 채택
   │
   ▼  ② 오케스트레이션
[TeamPipeline]
   plan   (planner · HIGH=opus)     → 플랜 아티팩트 + 태스크 도출
   exec   (executor · MEDIUM=sonnet) → Orchestrator가 병렬 디스패치(asyncio)
   verify (qa-tester · MEDIUM)       → 통과? ──┐
   │                                   실패 ↺  │  ③ Ralph
   └────────────── [RalphLoop] 완료까지 fix 반복 ┘
                   (PersistentMode: 미검증 동안 STOP 차단)
   │
   ▼  ④ 상태/아티팩트
[State]  control → project-memory.json (세션·메타)
         data    → artifacts/<sha256>.md (plan/result, 해시 검증)
```

실제 출력:

```text
$ uv run superharness demo
활성 스킬: ['ultrawork', 'ralph'] / 모드: ralph
목표: ultrawork: build a CSV parser, don't stop until tests pass
플랜: artifacts/8cb415c7…md
결과 아티팩트: 1개
  - artifacts/ed7365e2…md (sha256=ed7365e27032)
검증 완료: True (반복 1)
```

---

## 요구 사항 · 설치

- **Python 3.11+** (`enum.StrEnum`, `X | Y` 유니언, `datetime.UTC` 사용)
- 패키지/환경 관리: [**uv**](https://docs.astral.sh/uv/) (기본 `python3`가 3.9여도 uv가 3.12를 조달).
  미설치 시 `brew install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh | sh`.

```bash
uv python install 3.12              # 3.12 미설치 시 1회
uv venv --python 3.12               # ./.venv 생성 (.python-version=3.12 핀)
uv pip install -e ".[dev]"          # 코어 + 개발 도구 (오프라인)
# uv pip install -e ".[dev,anthropic]"  # 실제 Claude 백엔드까지
```

> uv 없이도 가능: 3.11+ 인터프리터를 마련한 뒤 `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`.

---

## 빠른 시작 (API 키 불필요)

기본 `mock` 프로바이더라 **네트워크/키 없이** 전부 동작한다. `uv run` 접두사를 붙이거나
`source .venv/bin/activate` 후 실행한다.

```bash
uv run superharness --help
uv run superharness ask "hello" --tier high       # 단일 완성 (티어→모델 라우팅)
uv run superharness state init                    # .superharness 상태 트리 + 샘플 아티팩트
uv run superharness skills list                   # 로드된 스킬/트리거
uv run superharness skills detect "ultrawork: refactor, don't stop until done"
uv run superharness agents run architect-high "결제 모듈 분석"
uv run superharness team "build a CSV parser"     # plan→exec→verify→fix
uv run superharness demo                          # 위 흐름 전체를 한 번에
```

| 명령 | 설명 |
|---|---|
| `ask <prompt> [--tier] [--provider]` | 프로바이더에 1회 질의 → 텍스트 |
| `state init` | 상태 디렉토리 트리 생성 + 샘플 아티팩트 기록 |
| `skills list` / `skills detect <prompt>` | 스킬 목록 / 키워드 감지·활성화 결과 |
| `agents run <name> <desc>` | 단일 에이전트 디스패치 + 아티팩트 기록 |
| `team <goal>` | Team 파이프라인(plan→exec→verify→fix) |
| `demo [prompt]` | 키워드→스킬→파이프라인→Ralph E2E |

---

## 오케스트레이션 개념

### 스킬 · 매직 키워드

스킬은 **YAML frontmatter + 마크다운 본문**이며, 프롬프트에 트리거가 들어가면 자동 활성화된다.

| 스킬 | 트리거 | 모드 |
|---|---|---|
| `ultrawork` | `ultrawork`, `ulw`, `uw` | ultrawork |
| `autopilot` | `autopilot`, `build me`, `end to end`, `e2e this` | autopilot |
| `ralph` | `ralph`, `don't stop`, `must complete`, `until done` | ralph |
| `team` | `team`, `team up`, `collaborate` | team |

- 매칭: **word-boundary 정규식 + longest-match 우선**, 스킬당 1회.
- 여러 스킬이 켜지면 **가장 강한 모드** 채택: `plain < ultrawork < autopilot < team < ralph`.
- 커스텀 스킬: `./.superharness/skills/*.md`(프로젝트) · `~/.superharness/skills/*.md`(유저) — 뒤가 override.

### 에이전트 매트릭스 (도메인 × 티어)

이름 규칙: MEDIUM은 도메인명 그대로, 그 외는 `도메인-티어`. (`agents run`의 인자로 사용)

| 도메인 | LOW | MEDIUM | HIGH |
|---|---|---|---|
| architect | `architect-low` | `architect` | `architect-high` |
| executor | `executor-low` | `executor` | `executor-high` |
| explore | `explore-low` | – | `explore-high` |
| designer | – | `designer` | – |
| planner | – | – | `planner-high` |
| critic | – | – | `critic-high` |
| qa-tester | – | `qa-tester` | – |
| security-reviewer | – | – | `security-reviewer-high` |

매트릭스는 데이터(`_DEFAULT_MATRIX`)다 — 새 에이전트는 행 추가로 끝(클래스 작성 불필요).

### 티어 → 모델

| 티어 | 기본 모델 | override |
|---|---|---|
| LOW | `claude-haiku-4-5` | `SUPERHARNESS_TIER_LOW` |
| MEDIUM | `claude-sonnet-4-6` | `SUPERHARNESS_TIER_MEDIUM` |
| HIGH | `claude-opus-4-8` | `SUPERHARNESS_TIER_HIGH` |

### 상태 · 아티팩트 (control / data plane 분리)

```
.superharness/
├── state/sessions/<id>/meta.json   # control: 세션 메타 + 이벤트 로그 (작은 JSON)
├── artifacts/<sha256>.<ext>        # data: 큰 내구성 산출물 (해시 주소)
├── project-memory.json             # control: 재사용 사실
└── plans/ specs/ notepads/ handoffs/   # (예약)
```

`ArtifactStore.write()`는 내용을 sha256으로 주소화하고 `ArtifactDescriptor`(kind·path·
content_hash·producer·created_at)를 돌려준다. control plane은 **descriptor만** 들고 다닌다.
`ReadPath`/`WritePath`(`NewType` + 검증 생성자)로 정적 구분 + 디렉토리 traversal을 차단한다.

---

## 라이브러리로 임베드

CLI 없이 코드에서 직접 엔진을 구동한다(전부 async — 동기 컨텍스트는 `anyio.run`으로 감싼다).

```python
import anyio
from superharness.agents import AgentRegistry
from superharness.config import load_settings
from superharness.hooks import HookBus, PersistentMode
from superharness.orchestration import TeamPipeline
from superharness.providers import get_provider
from superharness.skills import SkillRegistry
from superharness.state import StateLayout, ArtifactStore

settings = load_settings()                          # SUPERHARNESS_* 반영 (기본 mock)
layout = StateLayout(settings.state_dir).init()
hooks = HookBus()

skills = SkillRegistry.load()
activation = skills.activate("ultrawork: build it, don't stop until done")

pipeline = TeamPipeline(
    agents=AgentRegistry.default(),
    provider=get_provider(settings.provider),
    settings=settings,
    artifacts=ArtifactStore(layout),
    hooks=hooks,
    persistent=PersistentMode(hooks),
    injected_context=activation.injected_context,
)
result = anyio.run(lambda: pipeline.run("build a CSV parser"))
print(result.verified, result.iterations, len(result.results))
```

더 많은 예시(단일 에이전트 디스패치, 오케스트레이터, Ralph 루프, 아티팩트 직접 IO)는
[`docs/USAGE.md` §8](docs/USAGE.md)을 참고.

---

## 실제 Claude로 전환

```bash
uv pip install -e ".[dev,anthropic]"
SUPERHARNESS_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... uv run superharness ask "hello"
```

`get_provider(name)`이 유일한 교체 지점이다. `AnthropicProvider`의 요청 구성 규칙:
- MEDIUM/HIGH 티어에서만 `thinking={"type":"adaptive"}` + `output_config={"effort": ...}`.
- `temperature`/`top_p`/`budget_tokens`는 **절대 전송하지 않음**(해당 모델에서 400).
- 큰 `max_tokens`는 스트리밍으로 전송. `anthropic` import는 lazy(extra 미설치 시 불필요).

> 비용 주의: 실 백엔드에서 `team`/`demo`는 다수 에이전트를 호출한다. 먼저 mock/`--tier low`로 검증할 것.

---

## 설정 (환경변수)

모든 설정은 `SUPERHARNESS_` 접두사. 우선순위: 기본값 < 환경변수 < CLI 옵션. 샘플은 [`.env.example`](.env.example).

| 변수 | 기본값 | 설명 |
|---|---|---|
| `SUPERHARNESS_PROVIDER` | `mock` | `mock`(오프라인) / `anthropic` |
| `SUPERHARNESS_STATE_DIR` | `./.superharness` | 상태/아티팩트 루트 |
| `SUPERHARNESS_PARALLEL_EXECUTION` | `true` | 병렬 실행 on/off |
| `SUPERHARNESS_MAX_CONCURRENCY` | `4` | 오케스트레이터 동시성 상한 |
| `SUPERHARNESS_MAX_ITERATIONS` | `10` | Ralph/fix 루프 최대 반복 |
| `SUPERHARNESS_TIER_{LOW,MEDIUM,HIGH}` | haiku/sonnet/opus | 티어→모델 override |
| `SUPERHARNESS_LOG` | `INFO` | 로그 레벨 |
| `ANTHROPIC_API_KEY` | – | `anthropic` 프로바이더에서만 필요 |

---

## 테스트 · 품질

```bash
uv run pytest -q       # 40개 테스트 — 오프라인(mock), 네트워크/키 불필요
uv run ruff check .    # 린트
uv run mypy src        # 타입 체크
```

- **40개 테스트 · 라인 커버리지 95%** (오프라인 38 + 라이브 2 opt-in).
- 단위 테스트는 전부 `MockProvider`로 결정적·오프라인. `pytest-asyncio` auto 모드(마커 불필요).
- **라이브 API 테스트**(`live` 마커)는 기본 skip. 실제 1콜로 검증:
  ```bash
  uv pip install -e ".[dev,anthropic]"
  ANTHROPIC_API_KEY=sk-ant-... uv run pytest -m live
  ```

세 게이트(pytest/ruff/mypy)는 현재 모두 통과 — 변경 시 녹색 유지가 규칙.

---

## 프로젝트 구조

```
src/superharness/
  providers/      base(Provider Protocol · Tier) · mock · anthropic · 레지스트리
  skills/         skill · registry · keyword_detector · injector · builtin/*.md
  agents/         agent(도메인×티어) · registry(매트릭스)
  orchestration/  task(공유 큐) · orchestrator · pipeline(Team) · ralph
  hooks/          events · bus(+ persistent-mode STOP 가드)
  state/          paths(브랜디드) · descriptor · artifacts(data) · store(control)
  config.py       Settings(SUPERHARNESS_*) · TierModelMap
  cli.py          Typer: ask / state / skills / agents / team / demo
tests/            38 오프라인 + 2 라이브(opt-in)
docs/USAGE.md     상세 사용 설명서
examples/starter-app/   재사용 스타터 템플릿
```

---

## 새 프로젝트에서 재사용

슈퍼하네스를 **엔진으로 가져다 쓰는** 새 프로젝트 예제가 [`examples/starter-app/`](examples/starter-app/)에 있다
(커스텀 스킬·에이전트 + Team 파이프라인 + 자체 CLI). git 의존으로 연결한다:

```toml
# 소비 프로젝트의 pyproject.toml
[tool.uv.sources]
superharness = { git = "https://github.com/kbigdata/superharness", tag = "v0.1.0" }
```

uv가 클론→wheel 빌드→설치한다. PyPI/사내 인덱스 배포가 필요하면 `uv build`로 `dist/*.whl`을 만든다.

---

## 상태 · 로드맵

**상태**: v0.1.0 — 동작하는 MVP. 4대 패턴 전부 구현·검증, mock·실 Claude 양쪽 동작.

확장 여지(아키텍처 변경 없이 흡수 가능):
- 서브프로세스/CLI 워커 프로바이더(Codex/Gemini), LSP/AST 툴 레이어
- `wiki`/`learner`류 스킬(기존 `notepads/`·`project-memory.json` 활용)
- 원격 상태(`SUPERHARNESS_STATE_DIR` 공유 마운트), GitHub Actions CI

---

## 더 알아보기

- 상세 사용 설명서: [`docs/USAGE.md`](docs/USAGE.md) — CLI 전체 레퍼런스, 환경변수, 라이브러리 API, 확장, FAQ
- 스타터 템플릿: [`examples/starter-app/`](examples/starter-app/)
- 코드 작업 규약: [`CLAUDE.md`](CLAUDE.md)

라이선스: **MIT**.
