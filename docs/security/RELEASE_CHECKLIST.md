# RELEASE CHECKLIST

## Pre-release gates

- [ ] `uv sync --all-extras --dev`
- [ ] `uv run ruff check src tests`
- [ ] `uv run ruff format --check src tests`
- [ ] `uv run mypy src --strict`
- [ ] `uv run bandit -r src -lll`
- [ ] `uv run pytest --cov=mcpdb --cov-branch --cov-fail-under=90 -q`
- [ ] `uv run python -m mcpdb.cli --help`
- [ ] `uv run pip-audit --strict`

## Build and integrity

- [ ] `uv build` produced wheel and sdist
- [ ] `dist/checksums.txt` generated
- [ ] CycloneDX 1.5 SBOM generated at `sbom/mcpdb.cdx.json`
- [ ] `scripts/sign.sh` signed wheel, sdist, checksums, and SBOM
- [ ] verify signature bundles exist in `attestations/`

## Threat model and approval

- [ ] `docs/security/THREAT_MODEL.md` reviewed for this release
- [ ] Secondary maintainer sign-off recorded

## Publication

- [ ] Create annotated tag `vX.Y.Z`
- [ ] Trigger release workflow on tag push
- [ ] Verify draft release artifacts uploaded
- [ ] Verify immutable image tag (no `latest`) used in production docs
