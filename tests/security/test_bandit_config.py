import tomllib
from pathlib import Path


def load_bandit_config(pyproject_path: Path) -> dict[str, object]:
    pyproject_data = tomllib.loads(pyproject_path.read_text())
    return pyproject_data["tool"]["bandit"]


def test_bandit_config_excludes_tests(project_root: Path) -> None:
    bandit_config = load_bandit_config(project_root / "pyproject.toml")

    assert "tests" in bandit_config["exclude_dirs"]


def test_bandit_config_targets_src(project_root: Path) -> None:
    bandit_config = load_bandit_config(project_root / "pyproject.toml")

    assert bandit_config["targets"] == ["src"]
