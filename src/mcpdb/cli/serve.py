from __future__ import annotations

import logging

import anyio
import typer
import uvicorn
from mcp.server.stdio import stdio_server

from mcpdb.config.loader import load_settings
from mcpdb.server.app import build_http_app, build_server, select_transport

LOGGER = logging.getLogger(__name__)


def register_serve_command(
    ctx: typer.Context,
    transport: str | None,
    bind: str | None,
    port: int,
) -> None:
    settings = load_settings(ctx.obj.get("config"))
    host = bind or settings.security.bind_address

    if host == "0.0.0.0" and not settings.security.auth_enabled:
        raise typer.BadParameter(
            "Refusing non-loopback bind without auth_enabled=true"
        )  # OWASP A05

    selected = select_transport(settings, requested=transport)
    LOGGER.info("cli_action", extra={"action": "serve", "transport": selected})  # OWASP A09

    if selected == "http":
        server = build_server(settings)
        app = build_http_app(settings, server)
        uvicorn.run(app, host=host, port=port, log_level=str(ctx.obj.get("log_level", "info")))
        return

    server = build_server(settings)

    async def _serve_stdio() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    anyio.run(_serve_stdio)
