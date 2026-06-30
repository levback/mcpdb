from __future__ import annotations

import json
from pathlib import Path

import typer

from mcpdb.security.audit import HMACChainSink

audit_app = typer.Typer(help="Audit commands.")


def register_audit_command(path: Path, key: str) -> None:
    if not path.is_file():
        typer.echo("audit file does not exist")
        raise typer.Exit(code=3)

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)
    except json.JSONDecodeError:
        typer.echo("audit file is malformed")
        raise typer.Exit(code=3) from None

    if HMACChainSink.verify(path=path, key=key):
        typer.echo("audit chain is valid")
        return

    typer.echo("audit chain verification failed")
    raise typer.Exit(code=2)


@audit_app.command("verify")
def audit_verify_command(
    path: Path,
    key: str = typer.Option("test-key", "--key", help="HMAC key for verification."),
) -> None:
    register_audit_command(path, key)
