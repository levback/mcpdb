# mcpdb

![build](https://img.shields.io/badge/build-local-green)
![coverage](https://img.shields.io/badge/branch%20coverage-%3E%3D90%25-brightgreen)
![security](https://img.shields.io/badge/security-OWASP%20%2B%20NIST-blue)

mcpdb is a Python MCP server that exposes database query and introspection Tools across multiple Backends with policy enforcement and auditability.

![demo](https://dummyimage.com/1200x420/111827/ffffff&text=mcpdb+stdio+and+http+workflow)

## Features

- MCP transports: stdio and streamable HTTP
- Connector support: PostgreSQL, MySQL, SQLite, MongoDB
- Default-deny policy by Operation Class
- Read-only default Mode with explicit write enablement
- Query timeout and row Caps
- Audit Entry generation for Tool and authz outcomes

## Quickstart

```bash
git clone git@github.com:levback/mcpdb.git
cd mcpdb
./scripts/bootstrap.sh
uv run python -m mcpdb.cli config validate --file examples/01-minimal/mcpdb.yaml
uv run python -m mcpdb.cli serve --transport stdio --config examples/01-minimal/mcpdb.yaml
```

## Docs

- [Install](docs/install.md)
- [Quickstart](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [Security model](docs/security-model.md)
- [CLI usage](docs/cli/usage.md)
- [Config reference](docs/reference/config.md)

## Example stacks

- [Minimal SQLite](examples/01-minimal/README.md)
- [HTTP + OAuth](examples/02-prod-http-oauth/README.md)
- [Multi-backend + audit chain](examples/03-multimodal-audit/README.md)

## Security defaults

Do not run network-exposed HTTP with `auth_enabled=false` and `bind_host=0.0.0.0`. # OWASP A05

## Development commands

```bash
./scripts/test.sh
./scripts/security_scan.sh
./scripts/quality.sh all
uv run mkdocs build --strict
```
