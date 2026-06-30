# Install

## Requirements

- Python 3.12 or 3.13
- uv 0.4+
- Docker and Docker Compose (for example stacks)

## From source

```bash
git clone git@github.com:levback/mcpdb.git
cd mcpdb
uv sync --all-extras --dev
uv run pre-commit install
```

## Run CLI

```bash
uv run python -m mcpdb.cli --help
```

## Run quality gates

```bash
./scripts/test.sh
./scripts/security_scan.sh
```

## Build docs locally

```bash
uv run mkdocs serve
# or
uv run mkdocs build --strict
```

## Docker usage

The root Dockerfile builds the service image. For ready-to-run stacks, use the files under `examples/`.

## Unsafe settings warning

Do not expose HTTP transport publicly with `auth_enabled=false` and `bind_host=0.0.0.0`. # OWASP A05
