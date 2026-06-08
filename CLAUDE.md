# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**슈퍼하네스 (superharness)** — a standalone, framework-neutral **multi-agent orchestration
harness** in Python, implementing the core patterns of multi-agent orchestration as a runnable
MVP core. It is **not** a Claude Code plugin; it abstracts over multiple LLM backends and runs
fully offline by default (MockProvider). The distribution name, import package, and CLI command
are all `superharness`. A Korean research report (`oh-my-claudecode_조사보고서.md`) is the
original design source.

## Environment

Requires **Python 3.11+** (uses `enum.StrEnum`, `X | Y` unions, `datetime.UTC`). The machine's
default `python3` is 3.9 — use the dedicated env: `/Users/jeonghyun/miniforge3/envs/superharness312/bin/python`
(create with `conda create -n superharness312 python=3.12` if missing).

## Commands

```bash
PY=/Users/jeonghyun/miniforge3/envs/superharness312/bin/python
$PY -m pip install -e ".[dev]"            # core + dev tools (offline)
$PY -m pip install -e ".[dev,anthropic]"  # + real Claude backend
$PY -m pytest -q                          # full suite, offline (no network/keys)
$PY -m pytest tests/test_e2e_demo.py -q   # single test file
$PY -m ruff check .                        # lint (must stay clean)
$PY -m mypy src                            # type-check (must stay clean)
superharness demo                               # E2E CLI: detect→inject→pipeline→ralph→artifacts
```

All three gates (pytest / ruff / mypy) currently pass; keep them green.

## Architecture (the big picture)

Four core patterns map to layers under `src/superharness/`:

1. **Keyword → skill activation** (`skills/`): `KeywordDetector` scans a prompt for trigger
   words (word-boundary regex, longest-match, one match per skill); `SkillInjector` wraps the
   matched skills' bodies into a `<skill>` context block and picks the strongest `mode`
   (rank: plain < ultrawork < autopilot < team < ralph). Skills are markdown files with YAML
   frontmatter in `skills/builtin/` (plus optional `.superharness/skills/` project + `~/.superharness/skills/`
   user dirs; later overrides earlier by name).
2. **Multi-agent orchestration** (`orchestration/`, `agents/`): `TeamPipeline.run(goal)` does
   plan(planner) → derive tasks → exec(executor, parallel) → verify(qa-tester) → fix loop.
   `Orchestrator` fans out workers over a shared `TaskList` (atomic `claim/complete/fail` under
   one `asyncio.Lock`), bounded by `anyio.CapacityLimiter`. `AgentRegistry` is a **data-driven**
   domain×tier matrix — add agents by editing `_DEFAULT_MATRIX`, not by writing classes.
3. **Persistence / Ralph loop** (`orchestration/ralph.py`, `hooks/`): `RalphLoop` repeats
   verify→fix until `VerifyReport.complete` or `max_iterations`. `PersistentMode` registers a
   handler on the `STOP` lifecycle event in `HookBus` that **blocks** STOP while the goal is
   unverified (an in-process persistent-mode guard).
4. **State + tier routing** (`state/`, `config.py`, `providers/`): control/data plane split —
   `StateStore` holds small JSON (sessions, `project-memory.json`); `ArtifactStore` writes large
   durable outputs to `artifacts/<sha256>.<ext>` and returns an `ArtifactDescriptor`
   (kind/path/content_hash/producer/created_at) that the control plane passes around.
   `ReadPath`/`WritePath` are `NewType`s minted only by validating constructors (`as_read_path`/
   `as_write_path`) that block path traversal. `TierModelMap` resolves LOW/MEDIUM/HIGH →
   `claude-haiku-4-5` / `claude-sonnet-4-6` / `claude-opus-4-8`.

**Provider boundary:** all LLM access goes through the `Provider` Protocol
(`providers/base.py`). `get_provider(name)` is the only swap point — `mock` (default, offline,
records calls, echoes resolved model for routing assertions) or `anthropic`.

## Conventions & gotchas

- **Anthropic SDK shaping is load-bearing** (`providers/anthropic_provider.py`): on Opus/Sonnet
  tiers, thinking is `{"type":"adaptive"}` and effort goes in `output_config={"effort":...}`;
  **never** send `temperature`/`top_p`/`budget_tokens` (400 on Opus 4.8 / Sonnet 4.6); effort is
  omitted for Haiku 4.5. The `anthropic` import is lazy so mock-only installs need no dependency.
  Re-check `claude-api` skill before changing model ids or request params.
- **Avoid import cycles:** `agents/agent.py` imports `Task` only under `TYPE_CHECKING` (importing
  `orchestration.task` at runtime would trigger the orchestration package init → cycle).
- **Config via env:** all settings use the `SUPERHARNESS_` prefix (e.g. `SUPERHARNESS_PROVIDER`,
  `SUPERHARNESS_STATE_DIR`, `SUPERHARNESS_TIER_HIGH`); see `.env.example`. Default provider is `mock`, so
  everything runs offline unless `SUPERHARNESS_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` are set.
- **Async everywhere:** providers/agents/orchestrator are `async`; the CLI bridges with
  `anyio.run`. Tests use `pytest-asyncio` auto mode — write plain `async def test_...` (no marker).
- Code comments and skill content are in Korean; match that when editing.
