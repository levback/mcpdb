filepath: phases/02-config-and-secrets.md
# Phase 02 — Configuration & Secrets

> **Pre-reqs:** phase 01 merged.

## §1. Objective
Provide a single source of truth for runtime configuration: YAML file with `${env:NAME}` and `${vault:path}` secret refs, loaded into typed `pydantic-settings` models, validated at startup, with a `mcpdb config validate` CLI command.

## §2. SCOPE BOUNDARY
In scope:
- `src/mcpdb/config/` package: models, loader, secret resolver, validators.
- `mcpdb config validate` CLI subcommand.
- JSON-Schema export of the config model to `docs/reference/config.schema.json`.
- Round-trip and golden-file tests for the loader.

Out of scope:
- HTTP transport, DB connectors, MCP server (later phases).
- Actual vault backend (use a fake `MemoryVault` for tests; leave a `VaultProvider` ABC for phase 07).

## §3. Reference
DIRECTIVE.md §2 (pydantic-settings, pydantic-secrets), §5 (A02, A05). Glossary terms: Profile, SecretRef.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `src/mcpdb/config/models.py` | `McpDbSettings`, `Profile`, `Security`, `Limits`, `McpSettings` | 180 |
| `src/mcpdb/config/secrets.py` | `SecretRef`, `EnvProvider`, `MemoryVault`, `VaultProvider` ABC | 90 |
| `src/mcpdb/config/loader.py` | `load_settings(path) -> McpDbSettings`, file discovery | 70 |
| `src/mcpdb/config/validators.py` | cross-field validators (cap ranges, mode×write-allow) | 60 |
| `src/mcpdb/config/__init__.py` | public re-exports | 10 |
| `src/mcpdb/cli/config.py` | `mcpdb config validate`, `mcpdb config schema` | 60 |
| `tests/unit/config/test_models.py` | happy/edge/error cases for each model | 150 |
| `tests/unit/config/test_loader.py` | file not found, malformed YAML, refs unresolved | 120 |
| `tests/unit/config/test_secrets.py` | env precedence, missing ref, vault errors | 90 |
| `tests/properties/test_config_properties.py` | hypothesis: arbitrary valid configs round-trip | 70 |
| `tests/security/test_config_a02.py` | OWASP A02: secret never appears in repr/str/log | 60 |
| `tests/security/test_config_a05.py` | OWASP A05: dangerous defaults rejected | 50 |
| `examples/config/minimal.yaml` | 1 profile, sqlite, read-only | 20 |
| `examples/config/multi.yaml` | 2 profiles, pg + mongo | 30 |
| `docs/reference/config.schema.json` | generated via `mcpdb config schema` | generated |

## §5. Functional Requirements
1. `load_settings(None)` discovers `./mcpdb.yaml`, then `~/.config/mcpdb/config.yaml`, then `/etc/mcpdb/config.yaml`.
2. `${env:FOO}` resolves at call time, never written to the model as a literal.
3. `${vault:secret/db}` calls the injected `VaultProvider.resolve(key)`.
4. Models refuse invalid combinations: `mode=read_only` cannot have `allow_writes=true`; `query_timeout_ms<1` rejected; `bind_address=0.0.0.0` requires `auth_enabled=true`.
5. Schema export is JSON-Schema Draft 2020-12 with `$defs`.
6. `McpDbSettings.__repr__` redacts every SecretStr.

## §6. Test Plan (≥90% branch coverage on new code)
- `test_models_defaults_match_deny_by_default`
- `test_profile_rejects_unknown_backend`
- `test_profile_requires_dsn_or_discrete_fields`
- `test_security_rejects_bind_0_0_0_0_without_auth`
- `test_security_accepts_bind_127_0_0_1_without_auth`
- `test_limits_query_timeout_must_be_positive`
- `test_limits_max_rows_capped_at_one_million`
- `test_loader_env_var_precedence_over_yaml` — NIST SC-12
- `test_loader_unresolved_secret_ref_raises_with_path`
- `test_loader_yaml_duplicate_key_raises`
- `test_loader_yaml_anchors_supported`
- `test_secrets_env_provider_resolves_case_insensitive`
- `test_secrets_memory_vault_returns_value_once_then_redacts_log` — OWASP A02
- `test_secrets_missing_env_raises_with_required_name`
- `test_properties_round_trip_yaml_settings`
- `test_properties_validation_is_idempotent`
- `test_security_repr_never_contains_password_keyword`
- `test_security_logging_does_not_leak_secret_value` — capture stdlib logs
- `test_security_schema_export_has_no_secrets` — secret fields are `SecretStr`

## §7. Security Requirements
- A02: secrets use `pydantic.SecretStr`, redacted in `__repr__`, never logged.
- A05: defaults are `mode=read_only`, `auth_enabled=false` only for loopback.
- NIST SC-12/SC-13: secret refs documented; resolver is pluggable.

## §8. DoD
- [ ] `uv run mcpdb config validate examples/config/minimal.yaml` exits 0.
- [ ] `uv run mcpdb config validate examples/config/multi.yaml` exits 0.
- [ ] `uv run mcpdb config schema > docs/reference/config.schema.json` succeeds.
- [ ] Coverage ≥90% on `src/mcpdb/config/`.
- [ ] All OWASP A02/A05 tests pass; bandit clean; mypy strict clean.

## §9. Anti-Patterns
- No global `SETTINGS = load_settings()` — pass via DI.
- No bare `os.environ["FOO"]` — use the resolver.
- No `yaml.load()` — `yaml.safe_load` only.
