# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

## [0.1.0] - Unreleased

### Added

- Initial scaffolding for the mcpdb package, quality gates, and delivery scripts.

## Phase Report

### Phase 01

- Duration estimate: 90 minutes
- Files added: .editorconfig, .github/workflows/ci.yml, .gitignore, .pre-commit-config.yaml, Dockerfile, Makefile, docker-compose.yml, docs/security/SECURITY.md, scripts/dev.sh, scripts/security_scan.sh, scripts/test.sh, src/mcpdb/__main__.py, src/mcpdb/cli/__init__.py, src/mcpdb/cli/__main__.py, tests/__init__.py, tests/conftest.py, tests/security/test_bandit_config.py, tests/security/test_precommit_config.py, tests/unit/__init__.py, tests/unit/test_main.py, tests/unit/test_package_layout.py, tests/unit/test_version.py, uv.lock
- Files modified: CHANGELOG.md, README.md, pyproject.toml, src/mcpdb/__init__.py
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS; pytest PASS with 17 tests and 100% branch coverage; cli help PASS; pre-commit PASS
- Follow-ups: remote CI run still pending; Dockerfile and compose configuration are ready but local docker build/run validation remains blocked until a Docker daemon is available on this machine

### Phase 02

- Duration estimate: 130 minutes
- Files added: src/mcpdb/config/models.py, src/mcpdb/config/secrets.py, src/mcpdb/config/loader.py, src/mcpdb/config/validators.py, src/mcpdb/config/__init__.py, src/mcpdb/cli/config.py, tests/unit/config/test_models.py, tests/unit/config/test_loader.py, tests/unit/config/test_secrets.py, tests/properties/test_config_properties.py, tests/security/test_config_a02.py, tests/security/test_config_a05.py, examples/config/minimal.yaml, examples/config/multi.yaml, docs/reference/config.schema.json
- Files modified: CHANGELOG.md, pyproject.toml, uv.lock
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS; pytest PASS with 44 tests and 91.78% branch coverage; cli help PASS
- Follow-ups: pre-existing runtime warnings in legacy phase-01 runpy tests remain; no phase-02 failures outstanding

### Phase 03

- Duration estimate: 120 minutes
- Files added: src/mcpdb/db/__init__.py, src/mcpdb/db/base.py, src/mcpdb/db/policy.py, src/mcpdb/db/registry.py, src/mcpdb/db/fake.py, tests/unit/db/test_base.py, tests/unit/db/test_policy.py, tests/unit/db/test_registry.py, tests/unit/db/test_fake.py, tests/properties/test_policy_properties.py
- Files modified: CHANGELOG.md, pyproject.toml, uv.lock
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS; pytest PASS with 62 tests and 93.83% branch coverage; cli help PASS
- Follow-ups: pre-existing runtime warnings in legacy phase-01 runpy tests remain; no phase-03 failures outstanding
### Phase 04

- Duration estimate: 170 minutes
- Files added: src/mcpdb/db/sql/__init__.py, src/mcpdb/db/sql/base.py, src/mcpdb/db/sql/dialect.py, src/mcpdb/db/sql/postgres.py, src/mcpdb/db/sql/mysql.py, src/mcpdb/db/sql/sqlite.py, tests/unit/db/sql/test_dialect.py, tests/unit/db/sql/test_sql_base.py, tests/integration/db/sql/test_postgres.py, tests/integration/db/sql/test_mysql.py, tests/integration/db/sql/test_sqlite.py, tests/security/test_sql_a03.py
- Files modified: CHANGELOG.md, pyproject.toml, uv.lock
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (0 high/0 medium/0 low findings); pytest PASS with 388 tests (2 skipped) and 90.80% branch coverage; cli help PASS
- Follow-ups: pre-existing runtime warnings in legacy phase-01 runpy tests remain; no phase-04 failures outstanding

### Phase 05

- Duration estimate: 190 minutes
- Files added: src/mcpdb/db/nosql/__init__.py, src/mcpdb/db/nosql/query.py, src/mcpdb/db/nosql/mongo.py, tests/unit/db/nosql/test_query.py, tests/integration/db/nosql/test_mongo.py, tests/security/test_mongo_a03.py
- Files modified: CHANGELOG.md, pyproject.toml, uv.lock
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (0 high/0 medium/0 low findings); pytest PASS with 417 tests (4 skipped) and 92.01% branch coverage; cli help PASS
- Follow-ups: pre-existing runtime warnings in legacy phase-01 runpy tests remain; no phase-05 failures outstanding

### Phase 06

- Duration estimate: 220 minutes
- Files added: src/mcpdb/server/__init__.py, src/mcpdb/server/context.py, src/mcpdb/server/errors.py, src/mcpdb/server/resources.py, src/mcpdb/server/tools.py, src/mcpdb/server/app.py, tests/unit/server/test_context.py, tests/unit/server/test_errors.py, tests/unit/server/test_resources.py, tests/unit/server/test_tools.py, tests/integration/server/test_stdio_transport.py, tests/integration/server/test_http_transport.py
- Files modified: CHANGELOG.md, pyproject.toml, src/mcpdb/server/tools.py, tests/unit/server/test_tools.py, uv.lock
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (no issues identified); pytest PASS with 459 tests (5 skipped) and 92.43% branch coverage; cli help PASS
- Follow-ups: Starlette testclient deprecation warning for httpx/httpx2 and legacy runpy module warnings remain; phase-06 deliverables and gates are complete

### Phase 07

- Duration estimate: 240 minutes
- Files added: src/mcpdb/security/__init__.py, src/mcpdb/security/auth.py, src/mcpdb/security/authz.py, src/mcpdb/security/ratelimit.py, src/mcpdb/security/audit.py, src/mcpdb/security/secrets.py, tests/unit/security/test_auth.py, tests/unit/security/test_authz.py, tests/unit/security/test_ratelimit.py, tests/unit/security/test_audit_chain.py, tests/unit/security/test_security_secrets.py, tests/security/test_owasp_a01.py, tests/security/test_owasp_a02.py, tests/security/test_owasp_a07.py, examples/policies/deny_all.yaml, examples/policies/read_only_engineers.yaml
- Files modified: CHANGELOG.md, pyproject.toml, uv.lock, src/mcpdb/security/ratelimit.py, src/mcpdb/security/secrets.py, tests/unit/security/test_ratelimit.py, tests/security/test_owasp_a01.py, tests/security/test_owasp_a02.py, tests/security/test_owasp_a07.py, tests/unit/security/test_auth.py
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (0 high findings); pytest PASS with 495 tests (5 skipped) and 91.27% branch coverage; cli help PASS
- Follow-ups: Starlette testclient deprecation warning for httpx/httpx2 and legacy runpy module warnings remain; phase-07 high-risk hardening applied for stale rate-limit bucket pruning and stricter FileVault owner-permission checks

### Phase 08

- Duration estimate: 260 minutes
- Files added: src/mcpdb/cli/app.py, src/mcpdb/cli/serve.py, src/mcpdb/cli/doctor.py, src/mcpdb/cli/audit.py, src/mcpdb/cli/repl.py, src/mcpdb/cli/_render.py, tests/unit/cli/test_app.py, tests/unit/cli/test_serve.py, tests/unit/cli/test_doctor.py, tests/unit/cli/test_repl.py, tests/snapshot/cli/test_help_snapshots.py, docs/cli/usage.md
- Files modified: CHANGELOG.md, pyproject.toml, src/mcpdb/cli/__init__.py, src/mcpdb/cli/config.py, src/mcpdb/cli/serve.py, tests/unit/cli/test_app.py, tests/unit/cli/test_serve.py, tests/unit/cli/test_repl.py, docs/cli/usage.md
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (no issues identified); pytest PASS with 517 tests (5 skipped) and 91.05% branch coverage; cli help PASS
- Follow-ups: Starlette testclient deprecation warning for httpx/httpx2 and legacy runpy module warnings remain; targeted CLI branch coverage gaps persist in audit/config/doctor/repl modules though project-level coverage gate is green

### Phase 09

- Duration estimate: 210 minutes
- Files added: src/mcpdb/observability/__init__.py, src/mcpdb/observability/logging.py, src/mcpdb/observability/metrics.py, src/mcpdb/observability/tracing.py, src/mcpdb/observability/audit_integration.py, tests/unit/observability/__init__.py, tests/unit/observability/test_logging.py, tests/unit/observability/test_metrics.py, tests/unit/observability/test_tracing.py, tests/unit/observability/test_audit_integration.py, tests/security/test_log_injection_a09.py, tests/integration/observability/__init__.py, tests/integration/observability/test_otel_otlp.py
- Files modified: CHANGELOG.md, pyproject.toml, uv.lock
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (no issues identified); pytest PASS with 565 tests (6 skipped) and 91.19% branch coverage; cli help PASS
- Follow-ups: Starlette testclient deprecation warning for httpx/httpx2 and legacy runpy module warnings remain; OTel integration test is environment-dependent and skips when OTEL_EXPORTER_OTLP_ENDPOINT is unset

### Phase 10

- Duration estimate: 190 minutes
- Files added: tests/properties/test_mongo_filter_props.py, tests/properties/test_sql_query_props.py, tests/properties/test_policy_props.py, tests/properties/test_config_props.py, tests/fuzz/fuzz_jsonrpc.py, tests/fuzz/fuzz_config.py, tests/chaos/test_connector_chaos.py, tests/chaos/test_server_chaos.py, tests/mutation/mutmut.toml, tests/mutation/README.md, scripts/quality.sh
- Files modified: CHANGELOG.md, pyproject.toml, uv.lock
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (no issues identified); pytest PASS with 572 tests (6 skipped) and 91.27% branch coverage; cli help PASS
- Follow-ups: Starlette testclient deprecation warning for httpx/httpx2 and legacy runpy module warnings remain; optional atheris-based fuzz execution remains environment-dependent and is intentionally guarded in the fuzz harnesses

### Phase 11

- Duration estimate: 240 minutes
- Files added: mkdocs.yml, docs/index.md, docs/install.md, docs/quickstart.md, docs/architecture.md, docs/security-model.md, docs/reference/config.md, docs/recipes/claude-desktop.md, docs/recipes/cursor.md, docs/recipes/langchain.md, docs/faq.md, docs/adr/0001-why-mcp.md, docs/adr/0002-locked-stack.md, docs/adr/0003-security-defaults.md, examples/01-minimal/README.md, examples/01-minimal/docker-compose.yml, examples/01-minimal/mcpdb.yaml, examples/01-minimal/smoke.sh, examples/02-prod-http-oauth/README.md, examples/02-prod-http-oauth/docker-compose.yml, examples/02-prod-http-oauth/mcpdb.yaml, examples/02-prod-http-oauth/policy.yaml, examples/03-multimodal-audit/README.md, examples/03-multimodal-audit/docker-compose.yml, examples/03-multimodal-audit/mcpdb.yaml, examples/03-multimodal-audit/verify_audit_chain.sh, scripts/bootstrap.sh, scripts/release.sh, tests/unit/test_phase11_docs.py
- Files modified: .pre-commit-config.yaml, README.md, docs/cli/usage.md, pyproject.toml, uv.lock, CHANGELOG.md
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (no issues identified); pytest PASS with 585 tests (7 skipped) and 91.27% branch coverage; cli help PASS; mkdocs build --strict PASS
- Follow-ups: Material for MkDocs emits a non-fatal upstream ecosystem warning banner during build; Starlette testclient deprecation warning for httpx/httpx2 and legacy runpy module warnings remain

### Phase 12

- Duration estimate: 260 minutes
- Files added: .github/workflows/release.yml, docker-compose.prod.yml, docs/security/THREAT_MODEL.md, docs/security/RELEASE_CHECKLIST.md, scripts/sign.sh, tests/release/test_sbom_valid.py, tests/release/test_signatures_valid.py, tests/release/test_dockerfile_hardening.py, sbom/.gitkeep, attestations/.gitkeep
- Files modified: Dockerfile, pyproject.toml, scripts/release.sh, CHANGELOG.md, uv.lock
- Gate results: uv sync PASS; ruff PASS; ruff format PASS; mypy PASS; bandit PASS (no issues identified); pytest PASS with 596 tests (8 skipped) and 91.27% branch coverage; cli help PASS
- Follow-ups: keyless cosign signing and release workflow need a real tagged run in GitHub Actions to generate and verify live attestations; secondary maintainer sign-off in threat model remains pending
