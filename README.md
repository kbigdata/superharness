# 슈퍼하네스 (superharness)

> 여러 AI를 한 팀처럼 묶어, 하나의 목표를 **통과할 때까지 자동으로** 처리하게 해주는 작은 Python 엔진

[![CI](https://github.com/kbigdata/superharness/actions/workflows/ci.yml/badge.svg)](https://github.com/kbigdata/superharness/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/kbigdata/superharness?sort=semver)](https://github.com/kbigdata/superharness/releases/latest)
![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Built with uv](https://img.shields.io/badge/built%20with-uv-261230)

---

## 한눈에: 이게 뭔가요?

보통 AI에게 "CSV 파서 만들어줘"라고 하면 **한 번 답하고 끝**입니다.
슈퍼하네스는 그 일을 **여러 AI 일꾼에게 나눠 시키고, 결과를 검사하고, 통과 못 하면 다시
고치는 과정을 자동으로 반복**합니다. 마치 작은 개발팀처럼요.

```
당신: "CSV 파서 만들어줘"
  │
  ├─ 🧑‍💼 기획자 AI  → 할 일을 잘게 쪼갠다
  ├─ 🧑‍🔧 실행자 AI들 → 쪼갠 일을 나눠서 동시에 만든다
  ├─ 🕵️ 검사자 AI   → "목표를 만족했나?" 확인
  └─ ❌ 실패하면 → 자동으로 다시 고침 → 통과할 때까지 반복 ↺
```

- **"하네스(harness)"** 는 여러 마리의 말을 묶어 함께 부리는 *마구(馬具)* 를 뜻합니다.
  여기서는 **여러 AI를 묶어 한 방향으로 일하게 만드는 틀**이라는 의미입니다.
- 특정 도구(예: Claude Code)의 플러그인이 **아니라**, 어디서든 가져다 쓰는 **독립형 라이브러리 + CLI**입니다.

### 왜 편한가요?

| 장점 | 풀어 쓰면 |
|---|---|
| 🆓 **키 없이 공짜로 돌아감** | 기본이 "가짜 AI(mock)" 모드라 API 키·인터넷 없이 전 기능·전 테스트가 동작. 구조를 먼저 공짜로 익힐 수 있음 |
| 🔌 **키 하나로 진짜 전환** | `SUPERHARNESS_PROVIDER=anthropic` 한 줄이면 실제 Claude로 바뀜 |
| 🧩 **확장이 쉬움** | 새 작업 규칙은 마크다운 파일 한 개, 새 AI 역할은 표에 한 줄 추가로 끝 (코드 작성 거의 불필요) |
| 🪶 **가볍고 안전** | 무거운 의존성 없이 표준 라이브러리 위주. 파일 경로 탈출·결과 변조를 막는 안전장치 내장 |

---

## 핵심 용어 30초 정리

README 전체에서 쓰는 단어들입니다. 여기만 읽어도 나머지가 술술 읽힙니다.

| 용어 | 쉬운 뜻 |
|---|---|
| **에이전트(agent)** | 특정 역할(기획·실행·검사 등)을 맡은 **AI 일꾼 하나** |
| **스킬(skill)** | "이 단어가 나오면 이렇게 행동해라"를 적어둔 **마크다운 규칙 파일**. 프롬프트 속 키워드로 자동 발동 |
| **모드(mode)** | 스킬이 켜는 **작업 방식**. 예: `ralph` = "통과할 때까지 멈추지 마라" |
| **티어(tier)** | 일의 **난이도**(LOW·MEDIUM·HIGH). 난이도에 따라 싼/중간/비싼 모델을 자동 선택 |
| **프로바이더(provider)** | 실제로 AI를 호출하는 **백엔드**. `mock`(가짜·공짜) 또는 `anthropic`(진짜 Claude) |
| **아티팩트(artifact)** | 에이전트가 만든 **결과물 파일**(계획서·산출물). 내용 지문(해시)으로 저장돼 변조를 막음 |
| **오케스트레이션** | 여러 에이전트의 **순서·병렬·재시도를 조율**하는 것 |
| **하네스(harness)** | 위 모든 것을 묶어 굴리는 **전체 틀** = 이 프로젝트 |

---

## 목차

- [60초 체험 (설치 없이 흐름만)](#60초-체험-설치-없이-흐름만)
- [네 가지 핵심 기능](#네-가지-핵심-기능)
- [설치](#설치)
- [빠른 시작 (API 키 불필요)](#빠른-시작-api-키-불필요)
- [조금 더 깊이: 개념 설명](#조금-더-깊이-개념-설명)
- [v0.3.0에서 추가된 것](#v030에서-추가된-것)
- [코드에서 직접 쓰기 (라이브러리)](#코드에서-직접-쓰기-라이브러리)
- [실제 Claude로 전환](#실제-claude로-전환)
- [설정 (환경변수)](#설정-환경변수)
- [테스트 · 품질](#테스트--품질)
- [프로젝트 구조](#프로젝트-구조)
- [상태 · 로드맵](#상태--로드맵)

---

## 60초 체험 (설치 없이 흐름만)

명령 하나(`demo`)가 위에서 설명한 **기획→실행→검사→수정** 전체를 한 번에 보여줍니다.
무엇이 일어나는지 그림으로 먼저 보세요.

```
입력 프롬프트:  "ultrawork: build a CSV parser, don't stop until tests pass"
   │
   ▼  ① 키워드 감지 → 스킬 켜기
   "ultrawork", "don't stop" 단어를 발견 → 'ralph' 모드 켜짐("통과까지 멈추지 마")
   │
   ▼  ② 일 시키기 (오케스트레이션)
   기획자(planner)  → 할 일 목록 + 계획서 작성
   실행자(executor) → 목록을 동시에 처리 (병렬)
   검사자(qa-tester)→ 목표 만족? ──┐
   │                        실패 ↺ │  ③ 통과할 때까지 반복
   └──────────── 자동 수정 후 재검사 ┘
   │
   ▼  ④ 결과 저장
   계획서·산출물을 artifacts/<지문>.md 로 저장 (내용 해시로 변조 방지)
```

진짜 실행하면 이렇게 출력됩니다 (키 없이 가짜 AI로):

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

## 네 가지 핵심 기능

슈퍼하네스는 아래 4가지를 합쳐 동작합니다. (오른쪽은 실제 코드 위치 — 지금은 몰라도 됩니다.)

| 기능 | 한 줄 설명 | 코드 |
|---|---|---|
| ① **키워드 → 스킬** | 프롬프트에 특정 단어가 있으면 알맞은 작업 규칙(스킬)과 모드를 자동으로 켠다 | `KeywordDetector` + `SkillInjector` |
| ② **멀티에이전트 협업** | 할 일 목록을 여러 에이전트가 **나눠서 동시에** 처리 | `Orchestrator` + `TeamPipeline` |
| ③ **통과까지 반복 (Ralph)** | 검사→수정을 **목표 통과할 때까지** 반복(절반만 하고 끝내지 않음) | `RalphLoop` + `PersistentMode` |
| ④ **결과 저장 + 모델 선택** | 결과물을 안전하게 저장하고, 일 난이도에 맞는 모델을 자동 배정 | `ArtifactStore` + `TierModelMap` |

---

## 설치

준비물:
- **Python 3.11 이상**
- **[uv](https://docs.astral.sh/uv/)** (파이썬·패키지 관리 도구). 없으면:
  `brew install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - uv가 알아서 파이썬 3.12를 받아오므로, 시스템 파이썬이 낮아도 됩니다.

### 방법 A — 이 저장소를 직접 받아 써보기 (추천: 처음 보는 경우)

```bash
git clone https://github.com/kbigdata/superharness && cd superharness
uv venv --python 3.12            # ./.venv 가상환경 생성
uv pip install -e ".[dev]"       # 설치 (오프라인, 키 불필요)
uv run superharness demo         # 바로 체험
```

### 방법 B — 내 다른 프로젝트에서 라이브러리로 가져오기

```bash
# git 태그로 의존 (uv가 클론→빌드→설치까지)
uv add "superharness @ git+https://github.com/kbigdata/superharness@v0.3.0"
```

`pyproject.toml`에 고정하려면:
```toml
[tool.uv.sources]
superharness = { git = "https://github.com/kbigdata/superharness", tag = "v0.3.0" }
```

> 실제 Claude 백엔드까지 한 번에:
> `uv add "superharness[anthropic] @ git+https://github.com/kbigdata/superharness@v0.3.0"`
> 릴리스에 첨부된 wheel/sdist 파일은 [최신 릴리스 페이지](https://github.com/kbigdata/superharness/releases/latest)에서 받을 수 있습니다.

---

## 빠른 시작 (API 키 불필요)

기본이 `mock`(가짜 AI) 모드라 **인터넷·키 없이** 전부 동작합니다. 명령 앞에 `uv run`을 붙이세요.

```bash
uv run superharness --help                         # 전체 명령 보기
uv run superharness ask "hello" --tier high        # AI에게 1번 질문 (난이도 high)
uv run superharness skills list                    # 켤 수 있는 스킬 목록
uv run superharness skills detect "ultrawork: refactor, don't stop until done"
uv run superharness team "build a CSV parser"      # 팀으로 처리 (기획→실행→검사→수정)
uv run superharness demo                           # 위 전체 흐름을 한 번에 시연
```

### 명령 모음

| 명령 | 하는 일 |
|---|---|
| `ask <질문> [--tier] [--provider]` | AI에 한 번 물어보고 답을 받음 |
| `team <목표> [--learn]` | 팀 파이프라인 실행(기획→실행→검사→수정). `--learn` 시 성공 경험을 재사용 스킬로 추출 |
| `demo [프롬프트]` | 키워드→스킬→팀→반복까지 전 과정 시연 |
| `skills list / detect <프롬프트>` | 스킬 목록 / 어떤 스킬·모드가 켜지는지 미리 보기 |
| `skills proposed / promote / history / rollback / refine` | 자동 생성된 스킬의 검토·승격·이력·되돌리기·개선 |
| `agents run <이름> <설명>` | AI 일꾼 하나만 직접 실행 |
| `state init` | 상태/결과물 저장 폴더 만들기 |
| `memory add / query` | 기억(메모리) 추가 / 검색 *(v0.3.0)* |
| `codebase glob / read / grep / map` | 소스 코드 탐색: 파일 찾기·읽기·검색·구조 요약 *(v0.3.0)* |
| `wiki add / show` · `session search` | 누적 위키 기록 / 과거 세션 검색 *(v0.3.0)* |

---

## 조금 더 깊이: 개념 설명

### 스킬 — 키워드로 켜지는 작업 규칙

스킬은 **YAML 머리말 + 마크다운 본문**으로 된 파일입니다. 프롬프트에 트리거 단어가 들어가면 자동으로 켜집니다.

| 스킬 | 트리거 단어 | 모드(작업 방식) |
|---|---|---|
| `ultrawork` | `ultrawork`, `ulw`, `uw` | 강하게 밀어붙이는 모드 |
| `autopilot` | `autopilot`, `build me`, `end to end`, `e2e this` | 자율 진행 모드 |
| `ralph` | `ralph`, `don't stop`, `must complete`, `until done` | 통과까지 멈추지 않는 모드 |
| `team` | `team`, `team up`, `collaborate` | 협업 파이프라인 모드 |
| `karpathy` | `karpathy`, `카파시`, `코딩 규율` | 작업 규율 지침(신중·간결·외과적·목표주도) |

- 여러 스킬이 동시에 켜지면 **가장 강한 모드**가 이깁니다: `plain < ultrawork < autopilot < team < ralph`.
- 나만의 스킬은 `./.superharness/skills/*.md`(프로젝트) 또는 `~/.superharness/skills/*.md`(내 계정)에 두면 됩니다.

### 에이전트 — 역할별 AI 일꾼 (역할 × 난이도)

이름 규칙: 난이도 MEDIUM은 역할 이름 그대로, 나머지는 `역할-난이도`. (`agents run`의 첫 인자로 사용)

| 역할(도메인) | LOW | MEDIUM | HIGH |
|---|---|---|---|
| architect(설계) | `architect-low` | `architect` | `architect-high` |
| executor(실행) | `executor-low` | `executor` | `executor-high` |
| explore(탐색) | `explore-low` | – | `explore-high` |
| code-explorer(코드 탐색) | – | `code-explorer` | – |
| designer(UI) | – | `designer` | – |
| planner(기획) | – | – | `planner-high` |
| critic(비평) | – | – | `critic-high` |
| qa-tester(검사) | – | `qa-tester` | – |
| security-reviewer(보안) | – | – | `security-reviewer-high` |

> 새 역할 추가는 표(`_DEFAULT_MATRIX`)에 **한 줄** 넣으면 끝입니다. 클래스를 새로 쓸 필요가 없습니다.

### 티어 → 모델 (난이도가 모델을 고른다)

| 티어(난이도) | 자동 선택 모델 | 직접 바꾸기 |
|---|---|---|
| LOW(쉬움) | `claude-haiku-4-5` | `SUPERHARNESS_TIER_LOW` |
| MEDIUM(보통) | `claude-sonnet-4-6` | `SUPERHARNESS_TIER_MEDIUM` |
| HIGH(어려움) | `claude-opus-4-8` | `SUPERHARNESS_TIER_HIGH` |

### 결과물은 어디에 저장되나

```
.superharness/
├── state/sessions/<id>/meta.json   # 세션 메타 + 이벤트 로그 (작은 JSON)
├── artifacts/<지문>.<확장자>        # 큰 결과물 (내용 해시로 주소화 → 변조 방지)
├── project-memory.json             # 재사용할 작은 사실들 + 자동 적립 이벤트
├── memory.json                     # 구조화 메모리 (v0.3.0)
└── plans/ specs/ notepads/ handoffs/
```

작은 메타데이터(어떤 일을 했나)와 큰 결과물(실제 내용)을 **분리**해서 다룹니다. 큰 결과물은
내용 지문(sha256)으로 저장하고, 읽을 때 지문을 다시 검사해 **변조를 잡아냅니다**. 또 모든 경로는
저장 폴더 밖으로 못 나가게 막아(`../` 같은 탈출 차단) 안전합니다.

---

## v0.3.0에서 추가된 것

기존 4대 기능 위에 **"기억"과 "코드 읽기"** 능력이 더해졌습니다. (모두 키 없이 오프라인 동작)

- 🧠 **메모리 자동 적립** — 에이전트가 일하는 동안 활동이 `project-memory.json`에 자동으로 쌓입니다.
- 🔎 **구조화 메모리 + 검색/회상** — 메모리를 태그·네임스페이스로 저장하고 검색. 목표와 관련된
  기억을 자동으로 떠올려 작업에 끼워 넣습니다. → `superharness memory add / query`
- 📖 **코드베이스 읽기** — 소스 트리를 안전하게 탐색(`glob`/`read`/`grep`)하고, 파일별 함수·클래스
  구조를 요약한 **코드맵**을 만듭니다. → `superharness codebase glob / read / grep / map`
- 🗂 **프로젝트별 상태 격리** — `SUPERHARNESS_STATE_ROOT`를 켜면 프로젝트마다 상태가 분리됩니다.
- 📚 **위키 · 세션 검색** — 누적 지식 위키와 과거 세션 검색. → `superharness wiki`, `superharness session search`

---

## 코드에서 직접 쓰기 (라이브러리)

CLI 없이 파이썬 코드에서 엔진을 직접 굴릴 수 있습니다 (전부 async — 동기 코드에선 `anyio.run`으로 감쌈).

```python
import anyio
from superharness.agents import AgentRegistry
from superharness.config import load_settings
from superharness.hooks import HookBus, PersistentMode
from superharness.orchestration import TeamPipeline
from superharness.providers import get_provider
from superharness.skills import SkillRegistry
from superharness.state import StateLayout, ArtifactStore

settings = load_settings()                          # SUPERHARNESS_* 환경변수 반영 (기본 mock)
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

더 많은 예시(에이전트 하나만 실행, 오케스트레이터 직접 제어, Ralph 루프, 메모리/코드베이스 도구)는
[`docs/USAGE.md`](docs/USAGE.md)와 [`docs/하네스-가이드.md`](docs/하네스-가이드.md)를 보세요.

---

## 실제 Claude로 전환

```bash
uv pip install -e ".[dev,anthropic]"
SUPERHARNESS_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... uv run superharness ask "hello"
```

`mock` ↔ `anthropic` 전환은 환경변수 하나면 끝입니다. (내부적으로 `get_provider(name)` 한 곳에서만 갈아끼움)

> ⚠️ **비용 주의**: 실제 백엔드에서 `team`·`demo`는 여러 에이전트를 호출합니다.
> 먼저 `mock`이나 `--tier low`로 흐름을 확인한 뒤 쓰세요.

---

## 설정 (환경변수)

모든 설정은 `SUPERHARNESS_` 접두사입니다. 우선순위: 기본값 < 환경변수 < CLI 옵션. 샘플은 [`.env.example`](.env.example).

| 변수 | 기본값 | 설명 |
|---|---|---|
| `SUPERHARNESS_PROVIDER` | `mock` | `mock`(가짜·오프라인) / `anthropic`(진짜 Claude) |
| `SUPERHARNESS_STATE_DIR` | `./.superharness` | 상태·결과물 저장 폴더 |
| `SUPERHARNESS_STATE_ROOT` | (없음) | 설정 시 프로젝트별로 상태 분리 *(v0.3.0)* |
| `SUPERHARNESS_PARALLEL_EXECUTION` | `true` | 병렬 실행 켜기/끄기 |
| `SUPERHARNESS_MAX_CONCURRENCY` | `4` | 동시에 일하는 에이전트 최대 수 |
| `SUPERHARNESS_MAX_ITERATIONS` | `10` | "통과까지 반복"의 최대 횟수 |
| `SUPERHARNESS_TIER_{LOW,MEDIUM,HIGH}` | haiku/sonnet/opus | 난이도별 모델 바꾸기 |
| `SUPERHARNESS_LOG` | `INFO` | 로그 상세도 |
| `ANTHROPIC_API_KEY` | – | `anthropic` 모드에서만 필요 |

---

## 테스트 · 품질

```bash
uv run pytest -q       # 테스트 (오프라인, 키 불필요)
uv run ruff check .    # 코드 스타일 검사
uv run mypy src        # 타입 검사
```

- **테스트 90개 통과** + 라이브 API 테스트 3개(opt-in, 기본 건너뜀). 전부 `MockProvider`로 결정적·오프라인.
- 세 검사(pytest · ruff · mypy)는 현재 모두 통과하며, 코드 변경 시 **녹색 유지가 규칙**입니다.
- 실제 API로 1콜 검증하려면:
  ```bash
  uv pip install -e ".[dev,anthropic]"
  ANTHROPIC_API_KEY=sk-ant-... uv run pytest -m live
  ```

---

## 프로젝트 구조

```
src/superharness/
  providers/      AI 백엔드 — base(Provider 규약·Tier) · mock · anthropic
  skills/         스킬 시스템 — 로딩·키워드 감지·주입·자동생성(writer)·버전관리 · builtin/*.md(5개)
  agents/         에이전트 — agent(역할×난이도) · registry(매트릭스)
  orchestration/  조율 — task(공유 큐) · orchestrator · pipeline(Team) · ralph(반복) · learner(스킬 추출)
  state/          저장 — paths · artifacts(결과물) · store(메타) · memory(메모리) · wiki   ← v0.3.0 확장
  tools/          코드 이해 — codebase(glob/read/grep) · codemap(구조 요약)             ← v0.3.0 신규
  hooks/          이벤트 — events · bus(+ STOP 차단 가드)
  config.py       설정(SUPERHARNESS_*) · 티어→모델 매핑
  cli.py          명령들 — ask / team / demo / skills / agents / state / memory / codebase / wiki / session
tests/            테스트 90개(오프라인) + 3개(라이브 opt-in)
docs/             USAGE.md(상세 사용법) · 하네스-가이드.md(구조 안내)
examples/starter-app/   엔진으로 가져다 쓰는 스타터 템플릿
```

---

## 상태 · 로드맵

**현재 v0.3.0** — 4대 핵심 기능 + 자동 스킬 생성/개선/버전관리 + **메모리(자동 적립·검색·회상)** +
**코드베이스 읽기(grep/read/map)** + 프로젝트별 상태 격리 + 위키/세션 검색. mock·실 Claude 양쪽 동작.

### 구현됨 ✅
- **자동 스킬 생성(`learner`)** — 성공한 작업에서 재사용 스킬을 추출(검토용으로 격리 → 사람이 승격). `team --learn`
- **스킬 개선·버전관리** — `critic`이 스킬을 다듬고(`skills refine`), 이력·롤백 지원(`skills history`/`rollback`)
- **의미 기반 중복 제거** — 어휘 유사도(오프라인) + 선택적 LLM 판정
- **메모리 & 코드베이스 레이어 (v0.3.0)** — 위 [v0.3.0에서 추가된 것](#v030에서-추가된-것) 참고
- **CI** — GitHub Actions, Python 3.11/3.12/3.13 매트릭스 + 빌드 검증

### 확장 여지 (구조 변경 없이 흡수 가능)
- 다른 CLI 모델(Codex·Gemini) 프로바이더, LSP/AST 정밀 코드 분석 레이어
- 원격 공유 상태(`SUPERHARNESS_STATE_DIR`를 공유 마운트로)

### 의도적으로 보류 ⏸️
- **임베딩 기반 유사도** — 현재 규모(빌트인 스킬 소수)에선 어휘 유사도로 충분. 외부 의존(오프라인 원칙 위배)
  또는 무거운 로컬 모델을 요구하므로, 활성 스킬이 수십 개로 늘거나 의미 기반 *검색*이 필요해질 때 추가 예정.
  교체 지점(`Similarity` Protocol)은 이미 열려 있음.

---

## 더 알아보기

- 상세 사용 설명서: [`docs/USAGE.md`](docs/USAGE.md) — CLI 전체 레퍼런스 · 환경변수 · 라이브러리 API · FAQ
- 구조 안내(그림 위주): [`docs/하네스-가이드.md`](docs/하네스-가이드.md)
- 스타터 템플릿: [`examples/starter-app/`](examples/starter-app/)
- 코드 작업 규약: [`CLAUDE.md`](CLAUDE.md)

라이선스: **MIT**
