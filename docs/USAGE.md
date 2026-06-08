# 슈퍼하네스(superharness) 상세 사용 설명서

> 범용 멀티에이전트 오케스트레이션 하네스. 프레임워크 중립 Python 코어로, 기본값은 **완전 오프라인(mock)** 동작이며 환경변수 하나로 실제 Claude 백엔드로 전환된다.

- 버전: 0.1.0
- 대상 독자: 이 하네스를 CLI로 쓰거나, 라이브러리로 임베드하거나, 스킬/에이전트/프로바이더를 확장하려는 개발자
- 빠른 개요만 필요하면 루트 [`README.md`](../README.md)를, 코드 작업 규약은 [`CLAUDE.md`](../CLAUDE.md)를 참고

---

## 목차

1. [핵심 개념](#1-핵심-개념)
2. [설치 및 환경](#2-설치-및-환경)
3. [빠른 시작](#3-빠른-시작)
4. [CLI 완전 레퍼런스](#4-cli-완전-레퍼런스)
5. [환경변수 레퍼런스](#5-환경변수-레퍼런스)
6. [스킬과 매직 키워드](#6-스킬과-매직-키워드)
7. [에이전트 매트릭스](#7-에이전트-매트릭스)
8. [라이브러리 API 사용법](#8-라이브러리-api-사용법)
9. [실제 Claude 백엔드 연동](#9-실제-claude-백엔드-연동)
10. [확장: 스킬·에이전트·프로바이더](#10-확장-스킬에이전트프로바이더)
11. [상태와 아티팩트 구조](#11-상태와-아티팩트-구조)
12. [테스트와 품질 게이트](#12-테스트와-품질-게이트)
13. [문제 해결(FAQ)](#13-문제-해결faq)
14. [용어 사전](#14-용어-사전)

---

## 1. 핵심 개념

슈퍼하네스는 네 가지 패턴을 조합해 "자연어 의도 → 다중 에이전트 협업 → 검증 완료까지 지속"을 구현한다.

| 패턴 | 무엇을 하나 | 구현 모듈 |
|---|---|---|
| **① 키워드→스킬 활성화** | 프롬프트의 트리거 단어를 감지해 워크플로(스킬)와 실행 모드를 주입 | `skills/` |
| **② 멀티에이전트 오케스트레이션** | 공유 태스크 리스트를 도메인×티어 에이전트가 병렬 처리 | `orchestration/`, `agents/` |
| **③ 지속/검증 루프(Ralph)** | verify→fix를 목표 검증 완료까지 반복(부분 완료로 끝나지 않음) | `orchestration/ralph.py`, `hooks/` |
| **④ 상태/아티팩트 + 티어 라우팅** | control/data plane 분리, 해시 주소 아티팩트, 난이도→모델 매핑 | `state/`, `config.py`, `providers/` |

**control plane vs data plane**: 큐·세션·메타 같은 작은 운영 상태는 `StateStore`(JSON)에, plan/result/trace 같은 큰 산출물은 `ArtifactStore`(디스크)에 두고 `ArtifactDescriptor`(kind·path·content_hash·producer·created_at)로 참조한다.

**티어(Tier)**: 작업 난이도를 `LOW`/`MEDIUM`/`HIGH` 세 축으로 두고, `TierModelMap`이 각 티어를 모델 id로 해석한다.

| 티어 | 기본 모델 | 용도 |
|---|---|---|
| `LOW` | `claude-haiku-4-5` | 단순/빠른 작업 |
| `MEDIUM` | `claude-sonnet-4-6` | 일반 실행 |
| `HIGH` | `claude-opus-4-8` | 기획·비평·심층 분석 |

---

## 2. 설치 및 환경

### 요구 사항
- **Python 3.11+** (`enum.StrEnum`, `X | Y` 유니언, `datetime.UTC` 사용)
- 실제 Claude 사용 시: `ANTHROPIC_API_KEY` 환경변수 + `anthropic` extra

> 이 머신의 기본 `python3`는 3.9이므로, 전용 인터프리터를 사용한다:
> `/Users/jeonghyun/miniforge3/envs/superharness312/bin/python`
> (없으면 `conda create -n superharness312 python=3.12`)

### 설치

```bash
# 코어 + 개발 도구 (오프라인으로 모든 기능 동작)
pip install -e ".[dev]"

# 실제 Claude 백엔드까지
pip install -e ".[dev,anthropic]"
```

설치하면 `superharness` 명령과 `python -m superharness` 진입점이 생긴다.

| 항목 | 값 |
|---|---|
| distribution name | `superharness` |
| import 패키지 | `superharness` |
| CLI 명령어 | `superharness` (또는 `python -m superharness`) |

---

## 3. 빠른 시작

API 키 없이(기본 `mock` 프로바이더) 전부 동작한다.

```bash
superharness --help
superharness ask "hello"                    # 단일 완성
superharness state init                     # 상태 트리 생성 + 샘플 아티팩트
superharness skills list                    # 스킬/트리거 목록
superharness skills detect "ultrawork: refactor, don't stop until done"
superharness agents run executor "write a CSV parser"
superharness team "build a CSV parser"      # plan→exec→verify→fix
superharness demo                           # E2E: detect→inject→pipeline→ralph
```

`demo` 한 줄로 전체 파이프라인을 관찰할 수 있다:

```
$ superharness demo
활성 스킬: ['ultrawork', 'ralph'] / 모드: ralph
목표: ultrawork: build a CSV parser, don't stop until tests pass
플랜: artifacts/8cb415c7...md
결과 아티팩트: 1개
  - artifacts/ed7365e2...md (sha256=ed7365e27032)
검증 완료: True (반복 1)
```

---

## 4. CLI 완전 레퍼런스

명령은 `superharness <command> [options]` 형식이다. 모든 명령은 기본적으로 `SUPERHARNESS_*` 환경변수 설정을 따른다.

### `ask` — 단일 완성

프로바이더에 한 번 질의하고 텍스트를 출력한다.

```bash
superharness ask "프롬프트" [--tier low|medium|high] [--provider mock|anthropic]
```

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--tier` | `medium` | 사용할 티어(→모델 해석) |
| `--provider` | 설정값(`mock`) | 이 호출에 한정한 프로바이더 override |

예:
```bash
superharness ask "한 줄 요약: 멀티에이전트 하네스란?" --tier high
# → [mock:claude-opus-4-8] ...   (mock은 resolved 모델을 에코)
```

### `state init` — 상태 디렉토리 초기화

`SUPERHARNESS_STATE_DIR`(기본 `./.superharness`) 아래 디렉토리 트리를 만들고 샘플 아티팩트를 기록한다.

```bash
superharness state init
# 상태 디렉토리: /abs/path/.superharness
# 샘플 아티팩트: artifacts/<hash>.md (sha256=...)
```

### `skills list` — 스킬 목록

로드된 스킬과 트리거, 모드를 출력한다.

```bash
superharness skills list
# ultrawork    [ultrawork]  triggers: ultrawork, ulw, uw
# autopilot    [autopilot]  triggers: autopilot, build me, end to end, e2e this
# ralph        [ralph]      triggers: ralph, don't stop, must complete, until done
# team         [team]       triggers: team, team up, collaborate
```

### `skills detect` — 키워드 감지 + 활성화

프롬프트에서 트리거를 찾아 매칭/활성 스킬/모드/주입 컨텍스트를 보여준다.

```bash
superharness skills detect "ultrawork: build it, don't stop until done"
# 매칭: ['ultrawork', "don't stop"]
# 활성 스킬: ['ultrawork', 'ralph']
# 모드: ralph
# 파이프라인: ['architect', 'executor', 'qa-tester']
# --- 주입 컨텍스트 ---
# <skill name="ultrawork"> ... </skill>
# <skill name="ralph"> ... </skill>
```

### `agents run` — 단일 에이전트 실행

이름으로 에이전트 하나를 실행하고 산출 아티팩트와 라이프사이클 이벤트 수를 출력한다.

```bash
superharness agents run <agent-name> "태스크 설명"
```

예:
```bash
superharness agents run architect-high "결제 모듈 아키텍처를 분석하라"
# [architect-high] [mock:claude-opus-4-8] 결제 모듈 ...
# 아티팩트: artifacts/<hash>.md
# 라이프사이클: SubagentStart=1 SubagentStop=1
```

> 사용 가능한 에이전트 이름은 [§7 에이전트 매트릭스](#7-에이전트-매트릭스) 참고.

### `team` — Team 파이프라인

`plan → exec(병렬) → verify → fix(loop)`를 실행한다.

```bash
superharness team "목표" [--provider mock|anthropic]
# 목표: ...
# 플랜: artifacts/<hash>.md
# 결과 아티팩트: N개
# 검증 완료: True/False (반복 k)
```

### `demo` — E2E 데모

키워드 감지 → 스킬 주입 → Team 파이프라인 → Ralph 루프를 한 번에 보여준다.

```bash
superharness demo                 # 기본 프롬프트 사용
superharness demo "ultrawork: build X, until done"
```

---

## 5. 환경변수 레퍼런스

모든 설정은 `SUPERHARNESS_` 접두사를 쓴다. 우선순위는 **기본값 < 환경변수 < CLI 옵션**. 샘플은 [`.env.example`](../.env.example).

| 변수 | 기본값 | 설명 |
|---|---|---|
| `SUPERHARNESS_PROVIDER` | `mock` | `mock`(오프라인) 또는 `anthropic` |
| `SUPERHARNESS_STATE_DIR` | `./.superharness` | 상태/아티팩트 루트 디렉토리 |
| `SUPERHARNESS_PARALLEL_EXECUTION` | `true` | 병렬 에이전트 실행 on/off |
| `SUPERHARNESS_MAX_CONCURRENCY` | `4` | 오케스트레이터 동시성 상한 |
| `SUPERHARNESS_MAX_ITERATIONS` | `10` | Ralph/fix 루프 최대 반복 |
| `SUPERHARNESS_TIER_LOW` | `claude-haiku-4-5` | LOW 티어 모델 override |
| `SUPERHARNESS_TIER_MEDIUM` | `claude-sonnet-4-6` | MEDIUM 티어 모델 override |
| `SUPERHARNESS_TIER_HIGH` | `claude-opus-4-8` | HIGH 티어 모델 override |
| `SUPERHARNESS_LOG` | `INFO` | 로그 레벨(`DEBUG`/`INFO`/`WARNING`/...) |
| `ANTHROPIC_API_KEY` | (unset) | `anthropic` 프로바이더에서만 필요 |

예:
```bash
SUPERHARNESS_MAX_CONCURRENCY=8 SUPERHARNESS_LOG=DEBUG superharness team "..."
```

---

## 6. 스킬과 매직 키워드

스킬은 **YAML frontmatter + 마크다운 본문**으로 된 워크플로 단위다. 프롬프트에 트리거 단어가 들어가면 자동 활성화된다.

### 빌트인 스킬

| 스킬 | 트리거 | 모드 | 파이프라인 |
|---|---|---|---|
| `ultrawork` | `ultrawork`, `ulw`, `uw` | `ultrawork` | architect → executor → qa-tester |
| `autopilot` | `autopilot`, `build me`, `end to end`, `e2e this` | `autopilot` | planner → executor → qa-tester |
| `ralph` | `ralph`, `don't stop`, `must complete`, `until done` | `ralph` | — |
| `team` | `team`, `team up`, `collaborate` | `team` | planner → executor → qa-tester |

### 매칭 규칙
- **word-boundary 정규식**: 부분 단어 오탐 방지
- **longest-match 우선**: 더 구체적인 트리거가 이김
- **스킬당 1회**: 한 스킬은 최초 매칭만 기록

### 모드 결정(여러 스킬 동시 활성화 시)
가장 강한 모드를 채택한다: `plain < ultrawork < autopilot < team < ralph`.
예) `"ultrawork ... don't stop until done"` → ultrawork+ralph 활성 → **모드 = ralph**.

> 모드는 다운스트림 러너가 Team/Ralph 같은 실행 전략을 고를 때 쓰는 신호다. 활성화 결과(`injected_context`)는 에이전트의 system 프롬프트 앞에 붙는다.

---

## 7. 에이전트 매트릭스

에이전트는 **도메인 × 티어**로 정의된다. 이름 규칙: MEDIUM 티어는 도메인명 그대로, 그 외는 `도메인-티어`.

| 도메인 | LOW | MEDIUM | HIGH |
|---|---|---|---|
| 분석(architect) | `architect-low` | `architect` | `architect-high` |
| 실행(executor) | `executor-low` | `executor` | `executor-high` |
| 탐색(explore) | `explore-low` | — | `explore-high` |
| 프론트엔드(designer) | — | `designer` | — |
| 기획(planner) | — | — | `planner-high` |
| 비평(critic) | — | — | `critic-high` |
| 테스트(qa-tester) | — | `qa-tester` | — |
| 보안(security-reviewer) | — | — | `security-reviewer-high` |

`agents run <name>`의 `<name>`에는 위 표의 셀 이름을 그대로 쓴다.

`AgentRegistry.get(domain, tier)`는 정확한 셀이 없으면 같은 도메인의 인접 티어로 폴백한다(MEDIUM→HIGH→LOW 순). 매트릭스는 데이터(`_DEFAULT_MATRIX`)이므로 [§10](#10-확장-스킬에이전트프로바이더)에서 행만 추가하면 새 에이전트가 생긴다.

---

## 8. 라이브러리 API 사용법

CLI 없이 코드에서 직접 임베드할 수 있다. 모든 핵심 객체는 async이며, 동기 컨텍스트에서는 `anyio.run`으로 감싼다.

### 8.1 단일 완성

```python
import anyio
from superharness.providers import get_provider
from superharness.providers.base import CompletionRequest, Message
from superharness.config import load_settings
from superharness.providers.base import Tier

settings = load_settings()                 # SUPERHARNESS_* 반영
provider = get_provider(settings.provider) # 기본 mock
model = settings.tiers.resolve(Tier.HIGH)  # → claude-opus-4-8

async def main():
    res = await provider.complete(
        CompletionRequest(model=model, messages=[Message(role="user", content="hi")])
    )
    print(res.text, res.usage.output_tokens)

anyio.run(main)
```

### 8.2 키워드 감지 → 스킬 활성화

```python
from superharness.skills import SkillRegistry

reg = SkillRegistry.load()                 # builtin + 프로젝트/유저 스킬
activation = reg.activate("ultrawork: build it, don't stop until done")
print(activation.skills)            # ['ultrawork', 'ralph']
print(activation.mode)              # 'ralph'
print(activation.pipeline)          # ['architect', 'executor', 'qa-tester']
print(activation.injected_context)  # <skill>...</skill> 블록
```

### 8.3 Team 파이프라인 직접 구동

```python
import anyio
from superharness.agents import AgentRegistry
from superharness.config import load_settings
from superharness.hooks import HookBus, PersistentMode
from superharness.orchestration import TeamPipeline
from superharness.providers import get_provider
from superharness.state import StateLayout, ArtifactStore

settings = load_settings()
layout = StateLayout(settings.state_dir).init()
hooks = HookBus()
persistent = PersistentMode(hooks)          # STOP 차단 가드

pipeline = TeamPipeline(
    agents=AgentRegistry.default(),
    provider=get_provider(settings.provider),
    settings=settings,
    artifacts=ArtifactStore(layout),
    hooks=hooks,
    persistent=persistent,
)

result = anyio.run(lambda: pipeline.run("build a CSV parser"))
print(result.verified, result.iterations, len(result.results))
```

### 8.4 오케스트레이터 + 공유 태스크 리스트

```python
import anyio
from superharness.agents import AgentRegistry
from superharness.config import TierModelMap
from superharness.orchestration import Orchestrator, Task, TaskList
from superharness.providers import get_provider
from superharness.providers.base import Tier
from superharness.state import StateLayout, ArtifactStore

layout = StateLayout("./.superharness").init()
tasks = TaskList([
    Task(id=f"t{i}", domain="executor", tier=Tier.MEDIUM, description=f"subtask {i}")
    for i in range(5)
])
orch = Orchestrator(
    agents=AgentRegistry.default(),
    provider=get_provider("mock"),
    tiers=TierModelMap(),
    artifacts=ArtifactStore(layout),
    max_concurrency=4,
)
anyio.run(lambda: orch.run(tasks))
print(tasks.all_done(), [t.status for t in tasks.tasks])
```

`TaskList`는 `asyncio.Lock`으로 `claim/complete/fail`이 원자적이라, 각 태스크는 정확히 한 번만 실행된다.

### 8.5 Ralph 지속 루프 (제네릭)

```python
import anyio
from superharness.orchestration import RalphLoop, VerifyReport

state = {"n": 0}

async def verify() -> VerifyReport:
    state["n"] += 1
    return VerifyReport(complete=state["n"] >= 3, detail=f"attempt {state['n']}")

async def fix(report: VerifyReport) -> None:
    ...  # 실패 원인 보정

result = anyio.run(lambda: RalphLoop(verify, fix, max_iterations=10).run())
print(result.complete, result.iterations)   # True 3
```

`verify`/`fix`는 임의의 콜러블이므로 Team fix-loop든 독립 `/ralph`든 같은 루프를 재사용한다.

### 8.6 아티팩트 직접 읽기/쓰기

```python
from superharness.state import StateLayout, ArtifactStore

store = ArtifactStore(StateLayout("./.superharness").init())
desc = store.write("result", "최종 산출물 내용", producer="my-agent")
print(desc.path, desc.content_hash[:12])
assert store.read(desc) == "최종 산출물 내용"   # 읽을 때 해시 검증
```

`kind`는 `plan`/`spec`/`result`/`trace`/`note`를 지원(확장자 매핑). 내용이 변조되면 `read`가 `StateError`를 던진다.

---

## 9. 실제 Claude 백엔드 연동

`anthropic` extra를 설치하고 환경변수만 바꾸면 된다.

```bash
pip install -e ".[dev,anthropic]"
export ANTHROPIC_API_KEY=sk-ant-...
SUPERHARNESS_PROVIDER=anthropic superharness ask "한 줄 요약" --tier low
```

`AnthropicProvider`의 요청 구성 규칙(중요):
- MEDIUM/HIGH 티어(`claude-sonnet-4-6`/`claude-opus-4-8`)에서만 `thinking={"type":"adaptive"}` + `output_config={"effort": ...}`를 보낸다.
- `temperature`/`top_p`/`budget_tokens`는 **절대 전송하지 않는다**(해당 모델에서 400).
- LOW 티어(`claude-haiku-4-5`)에는 effort/thinking을 보내지 않는다.
- `max_tokens`가 크면 스트리밍으로 보내 HTTP 타임아웃을 피한다.
- `anthropic` import는 lazy — mock 전용 설치에서는 의존성이 없어도 된다.

> 비용 주의: 실제 백엔드에서는 `team`/`demo`가 다수의 에이전트를 호출한다. 먼저 `--tier low`나 mock으로 흐름을 검증한 뒤 전환할 것.

---

## 10. 확장: 스킬·에이전트·프로바이더

### 10.1 커스텀 스킬 추가

스킬 파일을 아래 디렉토리에 두면 자동 로드된다(뒤가 앞을 override):

| 스코프 | 경로 | 우선순위 |
|---|---|---|
| builtin | 패키지 내장 | 낮음 |
| 유저 | `~/.superharness/skills/*.md` | 중간 |
| 프로젝트 | `./.superharness/skills/*.md` | 높음 |

스킬 파일 예시 (`./.superharness/skills/deslop.md`):

```markdown
---
name: deslop
description: AI 생성물 정리 워크플로
triggers: ["deslop", "anti-slop"]
mode: team
pipeline: ["critic", "executor"]
---
변경 파일에서 군더더기(과도한 주석·죽은 코드·반복)를 제거하고 간결화하라.
```

frontmatter 필드: `name`(필수), `description`, `triggers`, `mode`(plain/ultrawork/autopilot/team/ralph), `pipeline`, `next_skill`.

확인:
```bash
superharness skills list
superharness skills detect "please deslop this module"
```

### 10.2 에이전트 매트릭스 확장

`src/superharness/agents/registry.py`의 `_DEFAULT_MATRIX`에 행을 추가한다. 클래스 작성 불필요.

```python
_DEFAULT_MATRIX = [
    # ... 기존 행 ...
    ("tracer", Tier.MEDIUM, "당신은 추적 에이전트입니다. 증거 기반으로 원인을 추적하세요."),
]
```

코드에서 직접 레지스트리를 구성할 수도 있다:

```python
from superharness.agents import AgentRegistry, AgentSpec
from superharness.providers.base import Tier

registry = AgentRegistry([
    AgentSpec(domain="writer", tier=Tier.LOW, name="writer",
              system_prompt="당신은 문서 작성자입니다."),
])
```

### 10.3 커스텀 프로바이더 작성

`Provider` Protocol(=`async complete(req) -> CompletionResult`)만 만족하면 어떤 백엔드든 꽂을 수 있다.

```python
from superharness.providers.base import CompletionRequest, CompletionResult, Usage

class EchoProvider:
    name = "echo"
    async def complete(self, req: CompletionRequest) -> CompletionResult:
        last = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        return CompletionResult(text=last.upper(), model=req.model, usage=Usage())

# 파이프라인/오케스트레이터/에이전트에 provider=EchoProvider() 로 주입
```

테스트에는 `MockProvider`를 쓰면 편하다(규칙 기반 결정적 응답):

```python
from superharness.providers import MockProvider

prov = (MockProvider()
        .when("weather", "sunny")                       # 부분문자열 매칭
        .when_fn(lambda r: "QA" in (r.system or ""), "PASS"))  # 임의 술어
```

---

## 11. 상태와 아티팩트 구조

`SUPERHARNESS_STATE_DIR`(기본 `./.superharness`) 아래 레이아웃:

```
.superharness/
├── state/
│   └── sessions/<session-id>/meta.json   # control plane: 세션 메타 + 이벤트 로그
├── artifacts/<sha256>.<ext>              # data plane: 큰 내구성 산출물
├── plans/                                # (예약) 플랜 아티팩트 영역
├── specs/                                # (예약) 스펙 영역
├── notepads/                             # (예약) 플랜 스코프 노트
├── handoffs/                             # (예약) 세션 간 핸드오프
└── project-memory.json                   # 재사용 가능한 작은 사실들
```

- **control plane**(`StateStore`): `create_session`, `get_session`, `append_event`, `read_memory`, `merge_memory`
- **data plane**(`ArtifactStore`): `write(kind, content, producer)→descriptor`, `read(descriptor)`(해시 검증)
- **브랜디드 경로**: `ReadPath`/`WritePath`(`NewType` + 검증 생성자)로 정적 구분 + 디렉토리 traversal 차단
- **중앙화**: `SUPERHARNESS_STATE_DIR`를 공유 경로로 두면 작업 디렉토리를 지워도 상태가 보존된다

---

## 12. 테스트와 품질 게이트

```bash
PY=/Users/jeonghyun/miniforge3/envs/superharness312/bin/python

$PY -m pytest -q                          # 전체(오프라인, 네트워크/키 불필요)
$PY -m pytest tests/test_e2e_demo.py -q   # 단일 파일
$PY -m ruff check .                        # 린트
$PY -m mypy src                            # 타입 체크
```

- 모든 테스트는 기본 `MockProvider`로 돌아 **네트워크/API 키가 필요 없다**.
- 테스트는 `pytest-asyncio` auto 모드 — 마커 없이 `async def test_...`로 작성.
- E2E 스모크(`tests/test_e2e_demo.py`)는 프롬프트 → 키워드 활성화 → Team 파이프라인 → verify 1회 실패 후 통과 → 아티팩트/메모리/라이프사이클 이벤트까지 한 번에 검증한다.

세 게이트(pytest/ruff/mypy)는 현재 모두 통과 상태이며, 변경 시 녹색 유지가 규칙이다.

---

## 13. 문제 해결(FAQ)

**Q. `superharness: command not found`**
설치 환경의 bin이 PATH에 없을 수 있다. `python -m superharness ...` 또는
`/Users/jeonghyun/miniforge3/envs/superharness312/bin/superharness`로 실행.

**Q. `Package 'superharness' requires a different Python: 3.9...`**
기본 python이 3.9다. 3.11+ 인터프리터(예: `superharness312` conda 환경)로 설치/실행.

**Q. `ProviderNotInstalled: anthropic 프로바이더는 ...`**
`anthropic` extra 미설치. `pip install -e ".[dev,anthropic]"` 후 `ANTHROPIC_API_KEY` 설정.

**Q. `team`/`demo`가 항상 "검증 완료: True (반복 1)"로 끝난다**
기본 mock은 qa-tester 출력에 "FAIL"이 없어 1회에 통과한다. 실패→재시도 루프를 보려면
mock에 규칙을 주거나(라이브러리 사용) 실제 프로바이더로 검증하라(테스트의 `QAStatefulProvider` 참고).

**Q. 상태 파일이 계속 쌓인다**
`.superharness/`는 런타임 산출물이며 `.gitignore`에 포함된다. 지워도 무방하다(필요 시 백업).

**Q. 모델을 바꾸고 싶다**
`SUPERHARNESS_TIER_{LOW,MEDIUM,HIGH}` 환경변수로 티어별 모델 id를 override.

---

## 14. 용어 사전

| 용어 | 의미 |
|---|---|
| **Tier** | 작업 난이도 축(LOW/MEDIUM/HIGH) → 모델로 해석 |
| **Provider** | LLM 백엔드 추상화(`async complete`). mock/anthropic |
| **Skill** | 트리거로 활성화되는 워크플로 단위(frontmatter+본문) |
| **Activation** | 감지된 스킬 + 주입 컨텍스트 + 결정된 모드 |
| **Agent** | 도메인×티어 실행 단위. 티어→모델 해석 후 provider 호출 |
| **Task / TaskList** | 공유 컨트롤플레인 작업 단위/큐(원자적 claim) |
| **Orchestrator** | TaskList에 대해 에이전트를 병렬 디스패치 |
| **TeamPipeline** | plan→exec→verify→fix(loop) 파이프라인 |
| **RalphLoop** | verify→fix를 완료까지 반복하는 지속 루프 |
| **PersistentMode** | 미검증 동안 STOP 이벤트를 차단하는 가드 |
| **ArtifactDescriptor** | data plane 산출물 참조(kind/path/hash/producer/created_at) |
| **control / data plane** | 작은 운영 상태 / 큰 내구성 산출물의 분리 |

---

*이 문서는 슈퍼하네스 v0.1.0 구현 기준이다. 코드가 바뀌면 동작/이름이 달라질 수 있으니, CLI는 `--help`로, 동작은 `tests/`로 최종 확인하라.*
