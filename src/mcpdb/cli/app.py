from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from mcpdb.__main__ import render_version
from mcpdb.cli._render import build_profiles_table, build_tools_table
from mcpdb.cli.audit import audit_app
from mcpdb.cli.config import config_app
from mcpdb.cli.doctor import register_doctor_command
from mcpdb.cli.repl import register_repl_command
from mcpdb.cli.serve import register_serve_command
from mcpdb.config.loader import ConfigLoadError, load_settings
from mcpdb.server.app import build_server_components

app = typer.Typer(
    add_completion=True,
    help="mcpdb command-line interface.",
    invoke_without_command=True,
)
app.add_typer(config_app, name="config")
app.add_typer(audit_app, name="audit")
tools_app = typer.Typer(help="Tool commands.")
profiles_app = typer.Typer(help="Profile commands.")
app.add_typer(tools_app, name="tools")
app.add_typer(profiles_app, name="profiles")
console = Console()


def _version_text() -> str:
    build_commit = os.getenv("MCPDB_BUILD_COMMIT", "dev")
    return f"{render_version()} ({build_commit})"


@app.callback()
def main_callback(
    ctx: typer.Context,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Path to mcpdb config file."),
    ] = None,
    log_level: Annotated[str, typer.Option("--log-level", help="Log level.")] = "info",
    version: Annotated[
        bool,
        typer.Option("--version", help="Show version and build commit."),
    ] = False,
) -> None:
    ctx.obj = {"config": config, "log_level": log_level}
    if version:
        typer.echo(_version_text())
        raise typer.Exit()


@tools_app.command("list")
def tools_list(ctx: typer.Context) -> None:
    settings = load_settings(ctx.obj.get("config"))
    built = build_server_components(settings)
    tool_names = sorted(tool.name for tool in built.tool_service.tool_definitions())
    console.print(build_tools_table(tool_names))


@profiles_app.command("list")
def profiles_list(ctx: typer.Context) -> None:
    settings = load_settings(ctx.obj.get("config"))
    rows = [{"name": profile.name, "backend": profile.backend} for profile in settings.profiles]
    console.print(build_profiles_table(rows))


@app.command("serve")
def serve_command(
    ctx: typer.Context,
    transport: str | None = typer.Option(None, "--transport", help="stdio or http"),
    bind: str | None = typer.Option(None, "--bind", help="Bind address."),
    port: int = typer.Option(8765, "--port", min=1, max=65535),
) -> None:
    register_serve_command(ctx, transport, bind, port)


@app.command("doctor")
def doctor_command(ctx: typer.Context) -> None:
    register_doctor_command(ctx)


@app.command("repl")
def repl_command(ctx: typer.Context) -> None:
    register_repl_command(ctx)


def entrypoint() -> None:
    try:
        app()
    except ConfigLoadError as error:
        typer.echo(f"Config error: {error}")
        raise typer.Exit(code=1) from error
