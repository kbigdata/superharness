"""agent-app CLI — 슈퍼하네스 엔진을 감싼 앱 전용 명령."""

from __future__ import annotations

import anyio
import typer

from agent_app.app import build_skills, run_goal, run_reviewer

app = typer.Typer(help="agent-app — 슈퍼하네스 기반 멀티에이전트 앱 스타터")


@app.command()
def run(goal: str) -> None:
    """목표를 키워드 활성화 → Team 파이프라인으로 실행한다."""
    activation, result = anyio.run(lambda: run_goal(goal))
    typer.echo(f"활성 스킬: {activation.skills} / 모드: {activation.mode}")
    typer.echo(f"플랜: {result.plan.path if result.plan else '-'}")
    typer.echo(f"결과 아티팩트: {len(result.results)}개")
    typer.echo(f"검증 완료: {result.verified} (반복 {result.iterations})")


@app.command()
def review(text: str) -> None:
    """커스텀 'reviewer' 에이전트로 텍스트/코드를 단일 리뷰한다."""
    result = anyio.run(lambda: run_reviewer(text))
    typer.echo(f"[{result.agent}] {result.output}")
    if result.artifact:
        typer.echo(f"아티팩트: {result.artifact.path}")


@app.command()
def skills() -> None:
    """builtin + 앱 전용 스킬 목록."""
    for s in build_skills().skills:
        trig = ", ".join(s.frontmatter.triggers)
        typer.echo(f"{s.name:12} [{s.frontmatter.mode}]  triggers: {trig}")


if __name__ == "__main__":
    app()
