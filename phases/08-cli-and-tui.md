filepath: phases/08-cli-and-tui.md
# Phase 08 — CLI & TUI (Typer + Rich)

> **Pre-reqs:** phase 07 merged.

## §1. Objective
Provide a polished, scriptable CLI: `serve`, `doctor`, `config validate|schema`, `tools list`, `profiles list`, `repl`, `audit verify`.

## §2. SCOPE BOUNDARY
In scope:
- `src/mcpdb/cli/app.py` — Typer root app, command loader.
- `src/mcpdb/cli/serve.py` — `serve --transport --bind --port`.
- `src/mcpdb/cli/doctor.py` — deep health: config, secrets, backend reachability, per-tool smoke.
- `src/mcpdb/cli/config.py` — `config validate`, `config schema`.
- `src/mcpdb/cli/audit.py` — `audit verify <path>`.
- `src/mcpdb/cli/repl.py` — interactive REPL with command-completion.
- `src/mcpdb/cli/_render.py` — Rich tables, themes.

Out of scope:
- Release packaging (phase 12).

## §3. Reference
DIRECTIVE.md §2 (typer, rich), §5 A05. Glossary: Profile, Tool, Resource.

## §4. Deliverables

| Path | Purpose | LoC |
|---|---|---|
| `src/mcpdb/cli/__init__.py` | typer app export | 20 |
| `src/mcpdb/cli/app.py` | root command, `--log-level`, `--config` | 60 |
| `src/mcpdb/cli/serve.py` | `serve` subcommand | 100 |
| `src/mcpdb/cli/doctor.py` | `doctor` subcommand | 180 |
| `src/mcpdb/cli/config.py` | `config validate|schema` | 80 |
| `src/mcpdb/cli/audit.py` | `audit verify` | 70 |
| `src/mcpdb/cli/repl.py` | interactive REPL (prompt_toolkit) | 160 |
| `src/mcpdb/cli/_render.py` | Rich helpers | 80 |
| `tests/unit/cli/test_app.py` | arg parsing | 80 |
| `tests/unit/cli/test_serve.py` | options, config overlay | 100 |
| `tests/unit/cli/test_doctor.py` | each check independently | 200 |
| `tests/unit/cli/test_repl.py` | scripted input → expected output | 150 |
| `tests/snapshot/cli/test_help_snapshots.py` | `--help` golden outputs | 60 |
| `docs/cli/usage.md` | examples, env vars, exit codes | 120 |

## §5. Functional Requirements
1. `mcpdb --version` prints version + build commit.
2. `mcpdb serve --transport http --bind 127.0.0.1 --port 8765` boots HTTP transport.
3. `mcpdb doctor` exits 0 if all backends reachable and config valid; 1 with categorized failures.
4. `mcpdb config validate PATH` exits 0/2 (valid/invalid).
5. `mcpdb config schema` emits JSON-Schema to stdout.
6. `mcpdb audit verify PATH` exits 0 (clean) / 2 (tampered) / 3 (malformed).
7. `mcpdb tools list` prints table: name, op_class, profiles.
8. `mcpdb repl` is a Typer REPL with `/help`, `/profiles`, `/tools`, `/ping`, `/query`.

## §6. Test Plan
- `test_app_version_flag`
- `test_app_unknown_subcommand_exits_2`
- `test_serve_overrides_bind_from_cli`
- `test_serve_rejects_non_loopback_without_auth`
- `test_doctor_reports_config_ok`
- `test_doctor_reports_secret_missing`
- `test_doctor_reports_unreachable_postgres`
- `test_doctor_reports_unreachable_mongo`
- `test_doctor_exits_zero_on_all_green`
- `test_config_validate_minimal_yaml_exits_0`
- `test_config_validate_invalid_yaml_exits_2`
- `test_config_schema_outputs_valid_json_schema`
- `test_audit_verify_clean_chain_exits_0`
- `test_audit_verify_tampered_exits_2`
- `test_help_snapshots_match_golden` — for every subcommand
- `test_repl_handles_query_command`
- `test_repl_handles_unknown_command_gracefully`

## §7. Security Requirements
- A05: refuse `--bind 0.0.0.0` when `auth_enabled=false` (loopback only).
- A09: every CLI action produces one structured log line.
- NIST AU-2: `doctor` and `serve` writes audit entry.

## §8. DoD
- [ ] All subcommands have `--help` and exit 0 on `--help`.
- [ ] `mcpdb doctor` and `mcpdb audit verify` exit codes match spec.
- [ ] Coverage ≥90% on `src/mcpdb/cli/`.
- [ ] Shell completions generated: `mcpdb --install-completion bash|zsh|fish`.

## §9. Anti-Patterns
- No `print()` for machine output — use Rich only when stdout is a TTY; JSON to stdout when piped.
- No click `prompt` with hidden secret value — use environment or stdin pipe.
