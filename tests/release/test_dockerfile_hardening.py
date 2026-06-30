from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def test_dockerfile_no_shell_in_runtime() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "distroless/static-debian12:nonroot" in dockerfile
    marker = "FROM gcr.io/distroless/static-debian12:nonroot"
    runtime_block = dockerfile.split(marker, maxsplit=1)[1]
    assert "sh -c" not in runtime_block
    assert "bash" not in runtime_block


def test_dockerfile_user_is_non_root() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "USER 65532:65532" in dockerfile


def test_dockerfile_no_capabilities_added() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "cap_add" not in dockerfile


def test_pip_audit_clean_on_lockfile() -> None:
    result = _run("uv", "run", "pip-audit", "--strict")
    assert result.returncode == 0, result.stderr + result.stdout


def test_threat_model_lists_each_component() -> None:
    text = (PROJECT_ROOT / "docs/security/THREAT_MODEL.md").read_text(encoding="utf-8")
    for component in (
        "CLI",
        "MCP server",
        "Connector layer",
        "Config loader",
        "Security controls",
        "Observability",
        "Release pipeline",
    ):
        assert component in text


def test_threat_model_residual_risk_field_present() -> None:
    text = (PROJECT_ROOT / "docs/security/THREAT_MODEL.md").read_text(encoding="utf-8")
    assert "Residual risk" in text


def test_hadolint_or_dive_optional_tools() -> None:
    hadolint = _run("which", "hadolint")
    dive = _run("which", "dive")
    if hadolint.returncode != 0 and dive.returncode != 0:
        pytest.skip("hadolint and dive not installed")
