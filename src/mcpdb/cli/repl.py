from __future__ import annotations

import asyncio
import shlex

import typer

from mcpdb.config.loader import load_settings
from mcpdb.config.models import McpDbSettings
from mcpdb.server.app import build_server_components
from mcpdb.server.context import RequestContext

HELP_TEXT = " /help /profiles /tools /ping <profile> /query <profile> <statement> /exit"


async def _run_ping(profile: str, settings_obj: McpDbSettings) -> dict[str, object]:
    built = build_server_components(settings_obj)
    return await built.tool_service.db_ping(
        profile=profile,
        request=RequestContext(correlation_id="repl", principal="repl-user"),
    )


async def _run_query(
    profile: str,
    statement: str,
    settings_obj: McpDbSettings,
) -> dict[str, object]:
    built = build_server_components(settings_obj)
    return await built.tool_service.db_query(
        profile=profile,
        statement=statement,
        request=RequestContext(correlation_id="repl", principal="repl-user"),
    )


def register_repl_command(ctx: typer.Context) -> None:
    settings = load_settings(ctx.obj.get("config"))
    typer.echo("mcpdb repl started. Use /help or /exit")

    while True:
        try:
            line = input("mcpdb> ").strip()
        except EOFError:
            break

        if not line:
            continue
        if line in {"/exit", "/quit"}:
            break
        if line == "/help":
            typer.echo(HELP_TEXT)
            continue
        if line == "/profiles":
            for configured_profile in settings.profiles:
                typer.echo(f"{configured_profile.name}:{configured_profile.backend}")
            continue
        if line == "/tools":
            built = build_server_components(settings)
            names = sorted(tool.name for tool in built.tool_service.tool_definitions())
            for name in names:
                typer.echo(name)
            continue

        try:
            tokens = shlex.split(line)
        except ValueError as error:
            typer.echo(f"parse error: {error}")
            continue

        if tokens[:1] == ["/ping"] and len(tokens) == 2:
            payload = asyncio.run(_run_ping(tokens[1], settings))
            typer.echo(str(payload))
            continue

        if tokens[:1] == ["/query"] and len(tokens) >= 3:
            query_profile = tokens[1]
            statement = " ".join(tokens[2:])
            payload = asyncio.run(_run_query(query_profile, statement, settings))
            typer.echo(str(payload))
            continue

        typer.echo("unknown command")
