from __future__ import annotations

import json
from importlib.metadata import distributions
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_sbom(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["bomFormat"] == "CycloneDX"
    assert payload["specVersion"] == "1.5"
    assert isinstance(payload.get("components"), list)
    return payload


def test_sbom_matches_cyclonedx_1_5_schema(tmp_path: Path) -> None:
    sbom_path = tmp_path / "mcpdb.cdx.json"
    sbom_path.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.5",
                "version": 1,
                "metadata": {"component": {"type": "application", "name": "mcpdb"}},
                "components": [{"type": "library", "name": "typer", "version": "0.16.0"}],
            }
        ),
        encoding="utf-8",
    )

    sbom = _load_sbom(sbom_path)
    assert sbom["version"] == 1


def test_sbom_includes_all_top_level_packages() -> None:
    release_script = (PROJECT_ROOT / "scripts/release.sh").read_text(encoding="utf-8")
    assert '"bomFormat": "CycloneDX"' in release_script
    assert '"specVersion": "1.5"' in release_script

    installed = {d.metadata.get("Name", "").lower() for d in distributions()}
    for package in ("mcp", "typer", "sqlalchemy", "pydantic"):
        assert package in installed
