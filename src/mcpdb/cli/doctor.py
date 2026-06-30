from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import typer

from mcpdb.config.loader import ConfigLoadError, load_settings
from mcpdb.config.models import Profile
from mcpdb.db.base import Context
from mcpdb.server import app as app_module

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DoctorResult:
    name: str
    ok: bool
    detail: str


async def _probe_profile(profile_name: str, profile: Profile) -> DoctorResult:
    connector = app_module._build_connector(profile)
    context = Context(profile=profile_name, request_id="doctor", principal="doctor")
    await connector.connect(context)
    try:
        latency_ms = await connector.ping(context)
    finally:
        await connector.close(context)

    return DoctorResult(profile_name, True, f"latency={latency_ms:.2f}ms")


def register_doctor_command(ctx: typer.Context) -> None:
    LOGGER.info("cli_action", extra={"action": "doctor"})  # NIST AU-2
    try:
        settings = load_settings(ctx.obj.get("config"))
    except ConfigLoadError as error:
        typer.echo(f"FAIL config {error}")
        raise typer.Exit(code=1) from error

    failures: list[DoctorResult] = []
    successes: list[DoctorResult] = []

    for profile in settings.profiles:
        try:
            result = asyncio.run(_probe_profile(profile.name, profile))
        except Exception as error:
            failures.append(DoctorResult(profile.name, False, str(error)))
            continue

        if result.ok:
            successes.append(result)
        else:
            failures.append(result)

    for result in successes:
        typer.echo(f"OK   {result.name} {result.detail}")
    for result in failures:
        typer.echo(f"FAIL {result.name} {result.detail}")

    if failures:
        raise typer.Exit(code=1)
