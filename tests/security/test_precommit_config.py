from pathlib import Path


def extract_hook_ids(config_text: str) -> set[str]:
    hook_ids: set[str] = set()
    for raw_line in config_text.splitlines():
        stripped_line = raw_line.strip()
        if stripped_line.startswith("- id:"):
            hook_ids.add(stripped_line.split(":", maxsplit=1)[1].strip())
    return hook_ids


def test_precommit_config_has_required_hooks(project_root: Path) -> None:
    config_text = (project_root / ".pre-commit-config.yaml").read_text()
    hook_ids = extract_hook_ids(config_text)

    assert {"ruff", "ruff-format", "mypy", "bandit", "uv-lock-check"} <= hook_ids


def test_precommit_config_has_minimum_version(project_root: Path) -> None:
    config_text = (project_root / ".pre-commit-config.yaml").read_text()

    assert "minimum_pre_commit_version:" in config_text
