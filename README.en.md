# superharness (슈퍼하네스)

[한국어](README.md) | **English**

> A small Python engine that harnesses multiple AIs as one team and drives a goal to completion — **automatically, until it passes**

[![CI](https://github.com/kbigdata/superharness/actions/workflows/ci.yml/badge.svg)](https://github.com/kbigdata/superharness/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/kbigdata/superharness?sort=semver)](https://github.com/kbigdata/superharness/releases/latest)
![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Built with uv](https://img.shields.io/badge/built%20with-uv-261230)

---

## At a glance: what is this?

Normally, when you ask an AI to "build a CSV parser," it **answers once and stops**.
superharness instead **splits the work across several AI workers, checks the result, and
automatically retries fixes until it passes** — like a small dev team.

```
You: "Build a CSV parser"
  │
  ├─ 🧑‍💼 Planner AI    → breaks the work into small tasks
  ├─ 🧑‍🔧 Executor AIs  → build the tasks in parallel
  ├─ 🕵️ QA AI         → checks "did we meet the goal?"
  └─ ❌ if it fails   → auto-fixes → repeats until it passes ↺
```

- A **"harness"** is the gear (tack) used to drive several horses together.
  Here it means **a frame that makes several AIs pull in the same direction**.
- It is **not** a plugin for any specific tool (e.g. Claude Code) — it's a **standalone library + CLI**
  you can drop into any project.

### Why it's convenient

| Benefit | In plain terms |
|---|---|
| 🆓 **Runs for free, no key** | The default is a "fake AI (mock)" mode, so every feature and every test runs with no API key or internet. Learn the structure for free first |
| 🔌 **One line to go real** | `SUPERHARNESS_PROVIDER=anthropic` switches to the real Claude |
| 🧩 **Easy to extend** | A new work rule is one markdown file; a new AI role is one row in a table (almost no code) |
| 🪶 **Light and safe** | Standard-library-first, no heavy deps. Built-in guards against path escapes and result tampering |

---

## Key terms in 30 seconds

These are the words used throughout this README. Read this and the rest flows easily.

| Term | Plain meaning |
|---|---|
| **agent** | A single **AI worker** with a specific role (planning, executing, QA, …) |
| **skill** | A **markdown rule file** saying "when this word appears, behave this way." Triggered by keywords in the prompt |
| **mode** | The **work style** a skill turns on. e.g. `ralph` = "don't stop until it passes" |
| **tier** | The **difficulty** of a task (LOW / MEDIUM / HIGH). Picks a cheap/mid/expensive model accordingly |
| **provider** | The **backend** that actually calls the AI. `mock` (fake, free) or `anthropic` (real Claude) |
| **artifact** | An **output file** produced by an agent (plan, result). Stored by content fingerprint (hash) to prevent tampering |
| **orchestration** | **Coordinating** the order, parallelism, and retries of multiple agents |
| **harness** | The **whole frame** that drives all of the above = this project |

---

## Table of contents

- [60-second tour (no install, just the flow)](#60-second-tour-no-install-just-the-flow)
- [The four core capabilities](#the-four-core-capabilities)
- [Install](#install)
- [Quick start (no API key)](#quick-start-no-api-key)
- [A bit deeper: concepts](#a-bit-deeper-concepts)
- [What's new in v0.3.0](#whats-new-in-v030)
- [Use it from code (library)](#use-it-from-code-library)
- [Switch to real Claude](#switch-to-real-claude)
- [Configuration (environment variables)](#configuration-environment-variables)
- [Testing · quality](#testing--quality)
- [Project layout](#project-layout)
- [Status · roadmap](#status--roadmap)

---

## 60-second tour (no install, just the flow)

A single command (`demo`) shows the whole **plan → execute → verify → fix** cycle described above.
See what happens as a picture first.

```
Input prompt:  "ultrawork: build a CSV parser, don't stop until tests pass"
   │
   ▼  ① detect keywords → turn on a skill
   Found "ultrawork", "don't stop" → 'ralph' mode on ("don't stop until it passes")
   │
   ▼  ② put the team to work (orchestration)
   planner    → writes a task list + plan
   executor   → processes the list in parallel
   qa-tester  → goal met? ──┐
   │                 fail ↺ │  ③ repeat until it passes
   └──── auto-fix, then re-verify ┘
   │
   ▼  ④ save results
   Save plan & outputs as artifacts/<fingerprint>.md (hash-addressed, tamper-evident)
```

Run it for real (with the fake AI, no key):

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

## The four core capabilities

superharness combines these four. (The right column is the actual code location — you don't need it yet.)

| Capability | One-line summary | Code |
|---|---|---|
| ① **keyword → skill** | When the prompt contains certain words, auto-enable the matching work rule (skill) and mode | `KeywordDetector` + `SkillInjector` |
| ② **multi-agent collaboration** | Several agents process a shared task list **in parallel** | `Orchestrator` + `TeamPipeline` |
| ③ **repeat until pass (Ralph)** | Repeat verify→fix **until the goal passes** (never stops half-done) | `RalphLoop` + `PersistentMode` |
| ④ **save results + pick model** | Store outputs safely and assign a model that fits the task's difficulty | `ArtifactStore` + `TierModelMap` |

---

## Install

Prerequisites:
- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (Python/package manager). If missing:
  `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - uv fetches Python 3.12 for you, so a low system Python is fine.

### Option A — clone and try this repo (recommended for first-timers)

```bash
git clone https://github.com/kbigdata/superharness && cd superharness
uv venv --python 3.12            # create ./.venv
uv pip install -e ".[dev]"       # install (offline, no key needed)
uv run superharness demo         # try it right away
```

### Option B — pull it into your own project as a library

```bash
# depend via git tag (uv clones → builds → installs)
uv add "superharness @ git+https://github.com/kbigdata/superharness@v0.3.0"
```

To pin it in `pyproject.toml`:
```toml
[tool.uv.sources]
superharness = { git = "https://github.com/kbigdata/superharness", tag = "v0.3.0" }
```

> With the real Claude backend in one go:
> `uv add "superharness[anthropic] @ git+https://github.com/kbigdata/superharness@v0.3.0"`
> Prebuilt wheel/sdist files are on the [latest release page](https://github.com/kbigdata/superharness/releases/latest).

---

## Quick start (no API key)

The default `mock` (fake AI) mode runs everything **without internet or a key**. Prefix commands with `uv run`.

```bash
uv run superharness --help                         # show all commands
uv run superharness ask "hello" --tier high        # ask the AI once (difficulty high)
uv run superharness skills list                    # list available skills
uv run superharness skills detect "ultrawork: refactor, don't stop until done"
uv run superharness team "build a CSV parser"      # run as a team (plan→exec→verify→fix)
uv run superharness demo                           # demo the whole flow at once
```

### Command list

| Command | What it does |
|---|---|
| `ask <prompt> [--tier] [--provider]` | Ask the AI once and get an answer |
| `team <goal> [--learn]` | Run the team pipeline (plan→exec→verify→fix). `--learn` extracts a reusable skill on success |
| `demo [prompt]` | Demo the full flow: keyword→skill→team→repeat |
| `skills list / detect <prompt>` | List skills / preview which skill & mode would fire |
| `skills proposed / promote / history / rollback / refine` | Review/promote/history/rollback/refine auto-generated skills |
| `agents run <name> <desc>` | Run a single AI worker directly |
| `state init` | Create the state/output folder |
| `memory add / query` | Add / search memory *(v0.3.0)* |
| `codebase glob / read / grep / map` | Explore source: find files, read, search, summarize structure *(v0.3.0)* |
| `wiki add / show` · `session search` | Cumulative wiki notes / search past sessions *(v0.3.0)* |

---

## A bit deeper: concepts

### Skills — work rules turned on by keywords

A skill is a file with **YAML front matter + a markdown body**. It auto-activates when a trigger word appears in the prompt.

| Skill | Trigger words | Mode (work style) |
|---|---|---|
| `ultrawork` | `ultrawork`, `ulw`, `uw` | push-hard mode |
| `autopilot` | `autopilot`, `build me`, `end to end`, `e2e this` | autonomous mode |
| `ralph` | `ralph`, `don't stop`, `must complete`, `until done` | don't-stop-until-pass mode |
| `team` | `team`, `team up`, `collaborate` | collaboration pipeline mode |
| `karpathy` | `karpathy`, `카파시`, `coding discipline` | work-discipline guidance (deliberate · simple · surgical · goal-driven) |

- If several skills fire, the **strongest mode** wins: `plain < ultrawork < autopilot < team < ralph`.
- Put your own skills in `./.superharness/skills/*.md` (project) or `~/.superharness/skills/*.md` (your account).

### Agents — role-based AI workers (role × difficulty)

Naming: MEDIUM difficulty uses the role name as-is; others are `role-tier`. (Used as the first argument to `agents run`.)

| Role (domain) | LOW | MEDIUM | HIGH |
|---|---|---|---|
| architect | `architect-low` | `architect` | `architect-high` |
| executor | `executor-low` | `executor` | `executor-high` |
| explore | `explore-low` | – | `explore-high` |
| code-explorer | – | `code-explorer` | – |
| designer | – | `designer` | – |
| planner | – | – | `planner-high` |
| critic | – | – | `critic-high` |
| qa-tester | – | `qa-tester` | – |
| security-reviewer | – | – | `security-reviewer-high` |

> Adding a new role is **one row** in the table (`_DEFAULT_MATRIX`). No new class needed.

### Tier → model (difficulty picks the model)

| Tier (difficulty) | Auto-selected model | Override |
|---|---|---|
| LOW (easy) | `claude-haiku-4-5` | `SUPERHARNESS_TIER_LOW` |
| MEDIUM (normal) | `claude-sonnet-4-6` | `SUPERHARNESS_TIER_MEDIUM` |
| HIGH (hard) | `claude-opus-4-8` | `SUPERHARNESS_TIER_HIGH` |

### Where results are stored

```
.superharness/
├── state/sessions/<id>/meta.json   # session meta + event log (small JSON)
├── artifacts/<fingerprint>.<ext>   # large outputs (hash-addressed → tamper-proof)
├── project-memory.json             # small reusable facts + auto-recorded events
├── memory.json                     # structured memory (v0.3.0)
└── plans/ specs/ notepads/ handoffs/
```

Small metadata (what was done) and large outputs (the actual content) are kept **separate**. Large
outputs are stored by content fingerprint (sha256) and **re-checked on read to catch tampering**.
All paths are also confined to the storage folder (no `../` escapes), so it's safe.

---

## What's new in v0.3.0

On top of the four core capabilities, **"memory" and "code reading"** were added. (All offline, no key.)

- 🧠 **Automatic memory recording** — agent activity is automatically accumulated into `project-memory.json` while they work.
- 🔎 **Structured memory + search/recall** — store memory with tags/namespaces and search it. Related memories
  are automatically recalled and injected into the work. → `superharness memory add / query`
- 📖 **Codebase reading** — safely explore the source tree (`glob`/`read`/`grep`) and build a **code map**
  summarizing functions/classes per file. → `superharness codebase glob / read / grep / map`
- 🗂 **Per-project state isolation** — set `SUPERHARNESS_STATE_ROOT` to isolate state per project.
- 📚 **Wiki · session search** — cumulative knowledge wiki and past-session search. → `superharness wiki`, `superharness session search`

---

## Use it from code (library)

You can drive the engine directly from Python without the CLI (all async — wrap with `anyio.run` in sync code).

```python
import anyio
from superharness.agents import AgentRegistry
from superharness.config import load_settings
from superharness.hooks import HookBus, PersistentMode
from superharness.orchestration import TeamPipeline
from superharness.providers import get_provider
from superharness.skills import SkillRegistry
from superharness.state import StateLayout, ArtifactStore

settings = load_settings()                          # reads SUPERHARNESS_* env vars (default mock)
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

For more examples (run a single agent, drive the orchestrator directly, the Ralph loop, memory/codebase tools),
see [`docs/USAGE.md`](docs/USAGE.md) and [`docs/하네스-가이드.md`](docs/하네스-가이드.md).

---

## Switch to real Claude

```bash
uv pip install -e ".[dev,anthropic]"
SUPERHARNESS_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-... uv run superharness ask "hello"
```

Switching `mock` ↔ `anthropic` is a single env var (internally swapped in one place, `get_provider(name)`).

> ⚠️ **Cost note**: with the real backend, `team`/`demo` call multiple agents.
> Verify the flow with `mock` or `--tier low` first.

---

## Configuration (environment variables)

All settings use the `SUPERHARNESS_` prefix. Priority: defaults < env vars < CLI options. Sample: [`.env.example`](.env.example).

| Variable | Default | Description |
|---|---|---|
| `SUPERHARNESS_PROVIDER` | `mock` | `mock` (fake, offline) / `anthropic` (real Claude) |
| `SUPERHARNESS_STATE_DIR` | `./.superharness` | state/output folder |
| `SUPERHARNESS_STATE_ROOT` | (unset) | when set, isolates state per project *(v0.3.0)* |
| `SUPERHARNESS_PARALLEL_EXECUTION` | `true` | enable/disable parallel execution |
| `SUPERHARNESS_MAX_CONCURRENCY` | `4` | max agents working at once |
| `SUPERHARNESS_MAX_ITERATIONS` | `10` | max rounds of "repeat until pass" |
| `SUPERHARNESS_TIER_{LOW,MEDIUM,HIGH}` | haiku/sonnet/opus | per-difficulty model override |
| `SUPERHARNESS_LOG` | `INFO` | log verbosity |
| `ANTHROPIC_API_KEY` | – | needed only in `anthropic` mode |

---

## Testing · quality

```bash
uv run pytest -q       # tests (offline, no key)
uv run ruff check .    # style check
uv run mypy src        # type check
```

- **90 tests passing** + 3 live API tests (opt-in, skipped by default). All deterministic & offline via `MockProvider`.
- The three checks (pytest · ruff · mypy) currently all pass; keeping them green is the rule on every change.
- To verify with one real API call:
  ```bash
  uv pip install -e ".[dev,anthropic]"
  ANTHROPIC_API_KEY=sk-ant-... uv run pytest -m live
  ```

---

## Project layout

```
src/superharness/
  providers/      AI backends — base(Provider protocol · Tier) · mock · anthropic
  skills/         skill system — loading · keyword detect · inject · auto-gen(writer) · versioning · builtin/*.md (5)
  agents/         agents — agent(role×tier) · registry(matrix)
  orchestration/  coordination — task(shared queue) · orchestrator · pipeline(Team) · ralph(loop) · learner(skill extract)
  state/          storage — paths · artifacts(outputs) · store(meta) · memory · wiki      ← v0.3.0 expanded
  tools/          code understanding — codebase(glob/read/grep) · codemap(structure)      ← v0.3.0 new
  hooks/          events — events · bus(+ STOP-blocking guard)
  config.py       settings(SUPERHARNESS_*) · tier→model mapping
  cli.py          commands — ask / team / demo / skills / agents / state / memory / codebase / wiki / session
tests/            90 offline tests + 3 live (opt-in)
docs/             USAGE.md (detailed usage) · 하네스-가이드.md (structure guide, Korean)
examples/starter-app/   starter template that consumes the engine
```

---

## Status · roadmap

**Currently v0.3.0** — the four core capabilities + auto skill generation/refinement/versioning +
**memory (auto-record · search · recall)** + **codebase reading (grep/read/map)** + per-project state
isolation + wiki/session search. Works with both mock and real Claude.

### Done ✅
- **Auto skill generation (`learner`)** — extract reusable skills from successful runs (quarantined for review → human promotes). `team --learn`
- **Skill refine · versioning** — `critic` polishes skills (`skills refine`); history & rollback (`skills history`/`rollback`)
- **Semantic dedup** — lexical similarity (offline) + optional LLM judge
- **Memory & codebase layers (v0.3.0)** — see [What's new in v0.3.0](#whats-new-in-v030)
- **CI** — GitHub Actions, Python 3.11/3.12/3.13 matrix + build verification

### Room to grow (absorbable without structural change)
- Other CLI-model providers (Codex · Gemini), an LSP/AST precise-analysis layer
- Remote shared state (point `SUPERHARNESS_STATE_DIR` at a shared mount)

### Deliberately deferred ⏸️
- **Embedding-based similarity** — at the current scale (few builtin skills), lexical similarity suffices.
  It would require an external dependency (violating the offline principle) or a heavy local model, so it's
  planned for when active skills grow to dozens or semantic *search* is needed. The swap point
  (`Similarity` protocol) is already in place.

---

## Learn more

- Detailed usage: [`docs/USAGE.md`](docs/USAGE.md) — full CLI reference · env vars · library API · FAQ
- Structure guide (diagram-heavy, Korean): [`docs/하네스-가이드.md`](docs/하네스-가이드.md)
- Starter template: [`examples/starter-app/`](examples/starter-app/)
- Code conventions: [`CLAUDE.md`](CLAUDE.md)

License: **MIT**
