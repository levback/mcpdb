from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd or PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def _markdown_files() -> list[Path]:
    docs_files = list((PROJECT_ROOT / "docs").rglob("*.md"))
    docs_files.append(PROJECT_ROOT / "README.md")
    return docs_files


def _extract_markdown_links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)


def _internal_links(path: Path) -> list[str]:
    links = []
    for link in _extract_markdown_links(path.read_text(encoding="utf-8")):
        if link.startswith(("http://", "https://", "mailto:")):
            continue
        if link.startswith("#"):
            continue
        links.append(link.split("#", 1)[0])
    return links


def test_mkdocs_build_is_strict_clean() -> None:
    result = _run("uv", "run", "mkdocs", "build", "--strict")
    assert result.returncode == 0, result.stderr + result.stdout


def test_mkdocs_includes_all_phase_reports() -> None:
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for phase in range(1, 11):
        assert f"### Phase {phase:02d}" in changelog


def test_examples_minimal_compose_file_is_valid() -> None:
    compose = PROJECT_ROOT / "examples/01-minimal/docker-compose.yml"
    parsed = yaml.safe_load(compose.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    assert "services" in parsed
    assert "mcpdb" in parsed["services"]


def test_examples_prod_http_oauth_includes_policy() -> None:
    config = PROJECT_ROOT / "examples/02-prod-http-oauth/mcpdb.yaml"
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    assert payload["security"]["auth_enabled"] is True
    assert "policy_file" in payload


def test_examples_multimodal_audit_includes_chain() -> None:
    config = PROJECT_ROOT / "examples/03-multimodal-audit/mcpdb.yaml"
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    assert payload["audit"]["chain_enabled"] is True
    assert "chain_key_ref" in payload["audit"]


def test_bootstrap_script_runs_dry_run(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    examples = repo / "examples/01-minimal"
    scripts.mkdir(parents=True)
    examples.mkdir(parents=True)

    source_script = PROJECT_ROOT / "scripts/bootstrap.sh"
    bootstrap = scripts / "bootstrap.sh"
    bootstrap.write_text(source_script.read_text(encoding="utf-8"), encoding="utf-8")
    bootstrap.chmod(bootstrap.stat().st_mode | stat.S_IXUSR)

    (examples / "mcpdb.yaml").write_text("profiles: []\n", encoding="utf-8")

    fake_uv = tmp_path / "uv"
    fake_uv.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    fake_uv.chmod(fake_uv.stat().st_mode | stat.S_IXUSR)

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env.get('PATH', '')}"

    result = subprocess.run(
        [str(bootstrap)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert (repo / "mcpdb.yaml").exists()


def test_readme_links_resolve() -> None:
    readme = PROJECT_ROOT / "README.md"
    for link in _internal_links(readme):
        target = (PROJECT_ROOT / link).resolve()
        assert target.exists(), f"missing README link target: {link}"


def test_adrs_have_status_field() -> None:
    for adr in sorted((PROJECT_ROOT / "docs/adr").glob("*.md")):
        text = adr.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"missing front matter: {adr.name}"
        end = text.find("\n---\n", 4)
        assert end > 0, f"invalid front matter: {adr.name}"
        header = text[4:end]
        assert re.search(r"^status:\s+\w+", header, flags=re.MULTILINE), adr.name


def test_adrs_index_lists_all_adrs() -> None:
    mkdocs_text = (PROJECT_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    for adr in sorted((PROJECT_ROOT / "docs/adr").glob("*.md")):
        rel = adr.relative_to(PROJECT_ROOT / "docs").as_posix()
        assert rel in mkdocs_text


def test_docs_no_broken_internal_links() -> None:
    for doc in _markdown_files():
        for link in _internal_links(doc):
            target = (doc.parent / link).resolve()
            assert target.exists(), f"broken link in {doc.name}: {link}"


def test_release_script_exists_and_is_executable() -> None:
    release_script = PROJECT_ROOT / "scripts/release.sh"
    assert release_script.exists()
    assert os.access(release_script, os.X_OK)


def test_scripts_still_present() -> None:
    script_names = (
        "dev.sh",
        "test.sh",
        "security_scan.sh",
        "quality.sh",
        "bootstrap.sh",
        "release.sh",
    )
    for name in script_names:
        assert (PROJECT_ROOT / "scripts" / name).exists()


def test_examples_have_readme() -> None:
    for example in ("01-minimal", "02-prod-http-oauth", "03-multimodal-audit"):
        assert (PROJECT_ROOT / "examples" / example / "README.md").exists()


def test_docker_compose_available_for_examples() -> None:
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("docker not installed")
    for example in ("01-minimal", "02-prod-http-oauth", "03-multimodal-audit"):
        result = _run("docker", "compose", "-f", f"examples/{example}/docker-compose.yml", "config")
        if result.returncode != 0 and "unknown shorthand flag" in (result.stderr + result.stdout):
            pytest.skip("docker compose plugin unavailable")
        assert result.returncode == 0, result.stderr + result.stdout
