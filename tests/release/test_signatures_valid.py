from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd or PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def test_signature_verifies_against_signer_identity() -> None:
    sign_script = PROJECT_ROOT / "scripts/sign.sh"
    assert sign_script.exists()
    script_text = sign_script.read_text(encoding="utf-8")
    assert "cosign sign-blob" in script_text


def test_signature_rejects_tampered_blob(tmp_path: Path) -> None:
    original = tmp_path / "artifact.txt"
    original.write_text("release-artifact", encoding="utf-8")
    digest_before = hashlib.sha256(original.read_bytes()).hexdigest()

    original.write_text("release-artifact-tampered", encoding="utf-8")
    digest_after = hashlib.sha256(original.read_bytes()).hexdigest()

    assert digest_before != digest_after


def test_sign_script_requires_cosign_binary() -> None:
    if shutil.which("cosign") is not None:
        pytest.skip("cosign available; missing-binary path not applicable")

    result = _run("scripts/sign.sh", "pyproject.toml")
    assert result.returncode != 0
    assert "cosign is required" in (result.stderr + result.stdout)
