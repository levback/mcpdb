import typer
from rich.console import Console

from mcpdb.__main__ import render_version

console = Console()


def main(
    version: bool = typer.Option(False, "--version", help="Show the package version."),
) -> None:
    """mcpdb command-line interface."""
    if version:
        console.print(render_version())
        return


if __name__ == "__main__":
    typer.run(main)
