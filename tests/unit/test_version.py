import tomllib
from pathlib import Path

from mcpdb import __version__


def test_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_version_matches_pyproject(project_root: Path) -> None:
    pyproject_data = tomllib.loads((project_root / "pyproject.toml").read_text())

    assert __version__ == pyproject_data["project"]["version"]
