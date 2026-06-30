filepath: phases/01-foundation.md
# Phase 01 — Foundation, Layout, Quality Gates

> **Pre-reqs:** none. This is the first phase.

## §1. Objective
Stand up a reproducible Python project `mcpdb` using `uv`, install and wire every static-analysis, testing, and security tool from the locked stack, and ensure the CI scaffold runs all quality gates in <3 minutes.

## §2. SCOPE BOUNDARY
In scope:
- Project metadata, dependencies, dev-dependencies (matches §2 of DIRECTIVE).
- `src/mcpdb/` package skeleton with empty `__init__.py` files.
- `tests/` skeleton with `conftest.py` and one smoke test.
- `.pre-commit-config.yaml`, `.editorconfig`, `.gitignore`.
- `.github/workflows/ci.yml` running all §3 gates on push & PR.
- `Dockerfile` (multi-stage, non-root, distroless runtime) — **must build**.
- `scripts/dev.sh`, `scripts/test.sh`, `scripts/security_scan.sh`.
- `CHANGELOG.md` with v0.1.0-unreleased section.
- `README.md` skeleton with a "Status: scaffolding" badge.

Out of scope (later phases):
- Any actual MCP code.
- Any actual DB code.
- Any auth, secrets, or transport.

## §3. Reference
Read DIRECTIVE.md (§3 gates) and phases/00-glossary.md.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `pyproject.toml` | uv project, deps per §2, ruff/mypy/bandit/pytest config | 80 |
| `uv.lock` | Pinned lockfile (committed) | generated |
| `src/mcpdb/__init__.py` | `__version__ = "0.1.0"` | 4 |
| `src/mcpdb/__main__.py` | `python -m mcpdb` → prints version | 8 |
| `src/mcpdb/cli/__init__.py` | empty | 1 |
| `tests/__init__.py` | empty | 1 |
| `tests/unit/__init__.py` | empty | 1 |
| `tests/conftest.py` | rootdir, asyncio_mode=auto, testpaths | 15 |
| `tests/unit/test_version.py` | asserts `__version__` exists & is str | 8 |
| `.pre-commit-config.yaml` | ruff, ruff-format, mypy, bandit, uv-lock-check | 25 |
| `.editorconfig` | 4-space indent, LF, UTF-8 | 15 |
| `.gitignore` | standard Python + .venv, .coverage, .mypy_cache | 30 |
| `.github/workflows/ci.yml` | jobs: install, lint, type, bandit, pytest | 60 |
| `Dockerfile` | multi-stage: builder (uv sync) → runtime (distroless) | 25 |
| `docker-compose.yml` | services: `mcpdb` (build); DBs added in later phases | 25 |
| `scripts/dev.sh` | `uv run pytest --watch` wrapper | 5 |
| `scripts/test.sh` | runs all gates, exits non-zero on any failure | 15 |
| `scripts/security_scan.sh` | bandit + pip-audit + gitleaks | 15 |
| `CHANGELOG.md` | Keep-a-Changelog format, empty 0.1.0 section | 25 |
| `README.md` | title, badges, status, quickstart coming in P11 | 40 |
| `docs/security/SECURITY.md` | reporting process (placeholder) | 10 |
| `Makefile` | phony targets: install, lint, type, test, sec, build, run | 25 |

## §5. Functional Requirements
1. `uv sync` completes offline-friendly with lockfile.
2. `uv run python -m mcpdb` prints `mcpdb 0.1.0`.
3. `uv run pytest` reports ≥1 passed, 0 failed.
4. CI green on a clean checkout using only cached deps.
5. `docker build .` succeeds; image runs `python -m mcpdb` as non-root.
6. Pre-commit hooks install on `uv run pre-commit install`.

## §6. Test Plan
- `tests/unit/test_version.py::test_version_is_string`
- `tests/unit/test_version.py::test_version_matches_pyproject` (parses pyproject)
- `tests/unit/test_main.py::test_module_runs_as_script` (subprocess)
- `tests/unit/test_main.py::test_exit_code_zero`
- `tests/unit/test_package_layout.py::test_no_namespace_packages` (`importlib.metadata.distribution("mcpdb")`)
- `tests/security/test_bandit_config.py` — proves `.bandit` present & excludes tests
- `tests/security/test_precommit_config.py` — parses yaml, asserts hooks present

(7 test functions total — enough to prove scaffolding works, gate ≥90%.)

## §7. Security Requirements
- A06: pin everything, enable `uv lock --check` in CI.
- A05: Dockerfile runs as `uid=65532`, no shell in runtime stage.
- A09: CI emits SARIF for bandit to `security-events` workflow.

## §8. DoD (Definition of Done)
- [ ] All §4 files committed.
- [ ] `uv run scripts/test.sh` exits 0.
- [ ] `docker build -t mcpdb:dev .` exits 0; `docker run --rm mcpdb:dev` prints version.
- [ ] `pre-commit run --all-files` exits 0.
- [ ] CI workflow visible; first run green (paste the link in report).

## §9. Anti-Patterns (auto-reject)
- Do NOT add a real MCP dep yet (phase 06).
- Do NOT add DB deps yet (phase 03+).
- Do NOT lower `--cov-fail-under` below 90.
- Do NOT install in editable mode inside Dockerfile.
