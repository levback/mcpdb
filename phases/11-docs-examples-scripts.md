filepath: phases/11-docs-examples-scripts.md
# Phase 11 — Docs, Examples, Dev Scripts

> **Pre-reqs:** phase 10 merged.

## §1. Objective
Make the project discoverable, installable, and reproducible for newcomers: full MkDocs site, runnable example stacks, dev scripts, and a complete README.

## §2. SCOPE BOUNDARY
In scope:
- `mkdocs.yml` (Material theme) + `docs/` tree: index, install, quickstart, architecture, security model, CLI reference, config reference, MCP integration recipes, FAQ.
- `examples/` directory: at least 3 ready-to-run stacks (minimal local SQLite; pg+http+oauth; full multimodal with audit chain).
- `scripts/` directory: `dev.sh`, `test.sh`, `security_scan.sh`, `quality.sh`, `release.sh` (alias of phase 12), `bootstrap.sh` (creates venv, syncs, configures pre-commit).
- `README.md` rewritten with badges, GIF, and quickstart.

Out of scope:
- Release pipeline internals (phase 12).
- Website hosting/CNAME (separate infra).

## §3. Reference
DIRECTIVE.md §2 (mkdocs-material optional), §7 phase index. OWASP A05 clear defaults in docs. NIST SA-5 (public docs match behavior).

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `mkdocs.yml` | site config, nav, palette, plugins | 60 |
| `docs/index.md` | landing | 80 |
| `docs/install.md` | from source, from PyPI, from Docker | 120 |
| `docs/quickstart.md` | 5-minute tutorial with SQLite + Claude Desktop | 200 |
| `docs/architecture.md` | diagram + component map | 160 |
| `docs/security-model.md` | OWASP/NIST mapping table | 200 |
| `docs/cli/usage.md` | every subcommand with examples | 300 |
| `docs/reference/config.md` | narrative companion to JSON-Schema | 200 |
| `docs/recipes/claude-desktop.md` | claude_desktop_config.json snippets | 80 |
| `docs/recipes/cursor.md` | mcp.json snippet | 60 |
| `docs/recipes/langchain.md` | Python client | 100 |
| `docs/faq.md` | troubleshooting, limits | 120 |
| `examples/01-minimal/` | compose + config + smoke test | 120 |
| `examples/02-prod-http-oauth/` | compose + policy + key gen | 250 |
| `examples/03-multimodal-audit/` | pg + mongo + audit chain verification | 300 |
| `scripts/bootstrap.sh` | one-shot dev env setup | 60 |
| `scripts/release.sh` | thin wrapper calling phase 12 | 20 |
| `README.md` | full rewrite | 200 |
| `docs/adr/0001-why-mcp.md` | rationale | 60 |
| `docs/adr/0002-locked-stack.md` | why each lib | 90 |
| `docs/adr/0003-security-defaults.md` | why default-deny | 80 |

## §5. Functional Requirements
1. `uv run mkdocs serve` works locally; `uv run mkdocs build --strict` exits 0.
2. Each `examples/0X-*/` is runnable with `docker compose up`; README inside.
3. `scripts/bootstrap.sh` idempotently creates `.venv`, syncs, installs pre-commit, copies a starter `mcpdb.yaml`.
4. README quickstart works end-to-end with no manual edits beyond pasting a config.

## §6. Test Plan
- `test_mkdocs_build_is_strict_clean`
- `test_mkdocs_includes_all_phase_reports`
- `test_examples_minimal_compose_file_is_valid`
- `test_examples_prod_http_oauth_includes_policy`
- `test_examples_multimodal_audit_includes_chain`
- `test_bootstrap_script_runs_dry_run` (mocks `uv`)
- `test_readme_links_resolve` (parse and HEAD-check)
- `test_adrs_have_status_field`
- `test_adrs_index_lists_all_adrs`
- `test_docs_no_broken_internal_links`

## §7. Security Requirements
- A05: documentation warns explicitly about unsafe settings (`bind=0.0.0.0` + `auth_enabled=false`).
- NIST SA-5: public docs and code behavior match; no doc-driven lies.

## §8. DoD
- [ ] `mkdocs build --strict` clean (no warnings, no broken links).
- [ ] All examples validated by `docker compose config` (or our minimal parser).
- [ ] README quickstart renders properly on GitHub (md lints clean).

## §9. Anti-Patterns
- No `pypi`/`DockerHub` instructions that haven't been verified.
- No copy-pasted docs from upstream projects without attribution.
