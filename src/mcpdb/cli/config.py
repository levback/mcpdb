from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from mcpdb.__main__ import render_version
from mcpdb.config import ConfigLoadError, McpDbSettings, load_settings

console = Console()
app = typer.Typer(add_completion=False, help="mcpdb command-line interface.")
config_app = typer.Typer(help="Configuration commands.")
app.add_typer(config_app, name="config")


@app.callback()
def root_callback(
    version: bool = typer.Option(False, "--version", help="Show the package version."),
) -> None:
    if version:
        console.print(render_version())
        raise typer.Exit()


@config_app.command("validate")
def validate_config(path: Path) -> None:
    try:
        load_settings(path)
    except ConfigLoadError as error:
        console.print(f"[red]Invalid config:[/red] {error}")
        if "Malformed YAML" in str(error):
            raise typer.Exit(code=2) from error
        raise typer.Exit(code=1) from error
    console.print(f"[green]Config is valid:[/green] {path}")


@config_app.command("schema")
def export_schema() -> None:
    schema = McpDbSettings.model_json_schema()
    typer.echo(json.dumps(schema, indent=2, sort_keys=True))


def entrypoint() -> None:
    app()
