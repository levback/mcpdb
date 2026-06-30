#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: scripts/release.sh vX.Y.Z" >&2
  exit 2
fi

version="$1"

case "$version" in
  v*)
    ;;
  *)
    echo "tag must start with 'v'" >&2
    exit 2
    ;;
esac

for cmd in uv python sha256sum git; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "required command missing: $cmd" >&2
    exit 1
  fi
done

if ! command -v cosign >/dev/null 2>&1; then
  echo "required command missing: cosign" >&2
  exit 1
fi

mkdir -p dist sbom attestations

# OWASP A10: fail-fast release path if any gate fails.
uv sync --all-extras --dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src --strict
uv run bandit -r src -lll
uv run pytest --cov=mcpdb --cov-branch --cov-fail-under=90 -q
uv run python -m mcpdb.cli --help
uv run pip-audit --strict

rm -f dist/*
uv build

python - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

from importlib.metadata import distributions

components: list[dict[str, str]] = []
for dist in sorted(distributions(), key=lambda d: (d.metadata.get("Name") or "").lower()):
    name = dist.metadata.get("Name")
    version = dist.version
    if not name or not version:
        continue
    components.append({"type": "library", "name": name, "version": version})

sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {"component": {"type": "application", "name": "mcpdb"}},
    "components": components,
}
Path("sbom/mcpdb.cdx.json").write_text(json.dumps(sbom, indent=2), encoding="utf-8")
PY

(
  cd dist
  sha256sum ./*.whl ./*.tar.gz > checksums.txt
)

scripts/sign.sh dist/*.whl dist/*.tar.gz dist/checksums.txt sbom/mcpdb.cdx.json

git tag -a "$version" -m "release $version"

echo "release artifacts prepared for $version"
