# agent-app — 슈퍼하네스 스타터 템플릿

슈퍼하네스(superharness)를 **오케스트레이션 엔진으로 재사용**하는 새 프로젝트의 최소 시작점.
기본 mock 프로바이더로 완전 오프라인 동작하며, 환경변수 하나로 실제 Claude로 전환된다.

## 이 템플릿이 보여주는 재사용 패턴

| # | 패턴 | 코드 |
|---|---|---|
| 1 | 커스텀 스킬 추가 (키워드→스킬) | `src/agent_app/skills/review.md` + `build_skills()` |
| 2 | 커스텀 에이전트 추가 (도메인×티어 매트릭스 확장) | `build_agents()` → `reviewer` |
| 3 | Team 파이프라인 재사용 (plan→exec→verify→fix) | `run_goal()` |
| 4 | 커스텀 에이전트 단일 디스패치 | `run_reviewer()` |
| 5 | 자체 CLI로 래핑 | `src/agent_app/cli.py` |

## 설치 (uv)

```bash
cd examples/starter-app
uv venv --python 3.12
uv pip install -e ".[dev]"      # superharness를 git 태그 v0.1.0에서 빌드·설치
# 실제 Claude까지:  uv pip install -e ".[dev,anthropic]"
```

> `pyproject.toml`의 `[tool.uv.sources]`가 슈퍼하네스를 **git 저장소의 릴리스 태그**로 의존한다
> (uv가 클론→wheel 빌드→설치). 현재는 원격이 없어 로컬 저장소(`file:///Users/jeonghyun/claude-test`)를
> 가리킨다. **GitHub로 푸시한 뒤**에는 다음으로 바꾼다:
> ```toml
> [tool.uv.sources]
> superharness = { git = "https://github.com/<you>/superharness", tag = "v0.1.0" }
> ```
> 빌드 산출물(wheel/sdist)을 직접 쓰려면 상위 레포에서 `uv build` 후 `dist/*.whl`을 인덱스/릴리스에 올린다.

## 실행 (오프라인)

```bash
uv run agent-app skills                                  # builtin + 앱 전용 스킬 목록
uv run agent-app run "code review: tighten the parser"   # 키워드 활성화 → Team 파이프라인
uv run agent-app review "def f(x): return x+1  # 리뷰해"  # 커스텀 reviewer 단일 디스패치
```

## 테스트

```bash
uv run pytest -q
uv run ruff check . && uv run mypy src
```

## 실제 Claude로 전환

```bash
SUPERHARNESS_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... uv run agent-app run "..."
```

## 다음 단계 (이 템플릿을 당신 앱으로)

1. `agent_app` → 당신 패키지명으로 변경 (`pyproject.toml`의 name/packages/scripts, 디렉토리)
2. `skills/`에 도메인 스킬 추가, `build_agents()`에 도메인 에이전트 추가
3. `run_goal()`을 당신 워크플로(트리거 → 작업 종류)로 교체
4. 필요하면 커스텀 `Provider`(Protocol: `async complete`)를 만들어 다른 백엔드 연결

자세한 API는 상위 레포의 [`docs/USAGE.md`](../../docs/USAGE.md) §8(라이브러리 API), §10(확장) 참고.
