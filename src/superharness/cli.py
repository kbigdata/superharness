"""superharness CLI — Typer 진입점. 각 단계가 독립 실행 가능한 표면을 노출한다."""

from __future__ import annotations

import anyio
import typer

from superharness.agents.registry import AgentRegistry
from superharness.config import load_settings
from superharness.hooks.bus import HookBus, PersistentMode
from superharness.hooks.events import LifecycleEvent
from superharness.orchestration.pipeline import TeamPipeline
from superharness.orchestration.task import Task
from superharness.providers import get_provider
from superharness.providers.base import CompletionRequest, Message, Tier
from superharness.skills.registry import SkillRegistry
from superharness.state.artifacts import ArtifactStore
from superharness.state.paths import StateLayout
from superharness.state.store import StateStore

app = typer.Typer(help="슈퍼하네스 — 범용 멀티에이전트 하네스 (프레임워크 중립 코어)")
skills_app = typer.Typer(help="스킬 / 키워드 활성화")
state_app = typer.Typer(help="상태 / 아티팩트")
agents_app = typer.Typer(help="에이전트 디스패치")
app.add_typer(skills_app, name="skills")
app.add_typer(state_app, name="state")
app.add_typer(agents_app, name="agents")


@app.command()
def ask(
    prompt: str,
    tier: str = typer.Option("medium", help="low | medium | high"),
    provider: str = typer.Option(None, help="mock | anthropic (기본: 설정값)"),
) -> None:
    """단일 완성. 프로바이더 in → 텍스트 out (기본 mock = 오프라인)."""
    settings = load_settings(provider=provider)
    prov = get_provider(settings.provider)
    model = settings.tiers.resolve(Tier(tier))

    async def _run() -> str:
        res = await prov.complete(
            CompletionRequest(model=model, messages=[Message(role="user", content=prompt)])
        )
        return res.text

    typer.echo(anyio.run(_run))


@state_app.command("init")
def state_init() -> None:
    """상태 디렉토리 트리를 생성하고 샘플 아티팩트를 기록한다."""
    settings = load_settings()
    layout = StateLayout(settings.state_dir).init()
    store = StateStore(layout)
    artifacts = ArtifactStore(layout)
    desc = artifacts.write("note", "superharness state initialized.", producer="cli")
    store.merge_memory({"initialized": True})
    typer.echo(f"상태 디렉토리: {layout.root}")
    typer.echo(f"샘플 아티팩트: {desc.path} (sha256={desc.content_hash[:12]})")


@skills_app.command("list")
def skills_list() -> None:
    """로드된 스킬과 트리거를 나열한다."""
    reg = SkillRegistry.load()
    for s in reg.skills:
        trig = ", ".join(s.frontmatter.triggers)
        typer.echo(f"{s.name:12} [{s.frontmatter.mode}]  triggers: {trig}")


@skills_app.command("detect")
def skills_detect(prompt: str) -> None:
    """프롬프트에서 트리거를 감지하고 활성화 결과(주입 컨텍스트 + 모드)를 출력한다."""
    reg = SkillRegistry.load()
    matches = reg.detect(prompt)
    activation = reg.injector.activate(matches)
    typer.echo(f"매칭: {[m.keyword for m in matches]}")
    typer.echo(f"활성 스킬: {activation.skills}")
    typer.echo(f"모드: {activation.mode}")
    if activation.pipeline:
        typer.echo(f"파이프라인: {activation.pipeline}")
    if activation.injected_context:
        typer.echo("--- 주입 컨텍스트 ---")
        typer.echo(activation.injected_context)


@agents_app.command("run")
def agents_run(
    name: str = typer.Argument(..., help="에이전트 이름 (예: executor, architect-high)"),
    description: str = typer.Argument(..., help="태스크 설명"),
) -> None:
    """단일 에이전트를 실행하고 산출 아티팩트를 기록한다."""
    settings = load_settings()
    layout = StateLayout(settings.state_dir).init()
    artifacts = ArtifactStore(layout)
    registry = AgentRegistry.default()
    agent = registry.get_by_name(name)
    prov = get_provider(settings.provider)
    hooks = HookBus()
    task = Task(id="cli", domain=agent.spec.domain, tier=agent.spec.tier, description=description)

    async def _run():
        return await agent.run(
            task, provider=prov, tiers=settings.tiers, artifacts=artifacts, hooks=hooks
        )

    result = anyio.run(_run)
    typer.echo(f"[{result.agent}] {result.output}")
    if result.artifact:
        typer.echo(f"아티팩트: {result.artifact.path}")
    typer.echo(
        f"라이프사이클: SubagentStart={hooks.fired(LifecycleEvent.SUBAGENT_START)} "
        f"SubagentStop={hooks.fired(LifecycleEvent.SUBAGENT_STOP)}"
    )


@app.command()
def team(goal: str, provider: str = typer.Option(None)) -> None:
    """Team 파이프라인: plan → exec(병렬) → verify → fix(loop)."""
    result = anyio.run(lambda: _run_pipeline(goal, provider))
    _print_pipeline(result)


@app.command()
def demo(prompt: str = "ultrawork: build a CSV parser, don't stop until tests pass") -> None:
    """E2E 데모: detect → inject → Team 파이프라인 → Ralph → 아티팩트."""

    async def _run():
        reg = SkillRegistry.load()
        activation = reg.activate(prompt)
        typer.echo(f"활성 스킬: {activation.skills} / 모드: {activation.mode}")
        return await _run_pipeline(prompt, None, injected=activation.injected_context)

    result = anyio.run(_run)
    _print_pipeline(result)


async def _run_pipeline(goal: str, provider: str | None, injected: str = ""):
    settings = load_settings(provider=provider)
    layout = StateLayout(settings.state_dir).init()
    artifacts = ArtifactStore(layout)
    store = StateStore(layout)
    store.create_session("cli-session")
    hooks = HookBus()
    persistent = PersistentMode(hooks)
    pipeline = TeamPipeline(
        agents=AgentRegistry.default(),
        provider=get_provider(settings.provider),
        settings=settings,
        artifacts=artifacts,
        hooks=hooks,
        persistent=persistent,
        injected_context=injected,
    )
    result = await pipeline.run(goal)
    store.merge_memory({"last_goal": goal, "verified": result.verified})
    return result


def _print_pipeline(result) -> None:
    typer.echo(f"목표: {result.goal}")
    typer.echo(f"플랜: {result.plan.path if result.plan else '-'}")
    typer.echo(f"결과 아티팩트: {len(result.results)}개")
    for d in result.results:
        typer.echo(f"  - {d.path} (sha256={d.content_hash[:12]})")
    typer.echo(f"검증 완료: {result.verified} (반복 {result.iterations})")


if __name__ == "__main__":
    app()
