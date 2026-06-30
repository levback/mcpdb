# mcpdb

mcpdb is an MCP database server that lets agents query multiple database Backends through one audited, policy-driven interface.

## What you get

- MCP transports: stdio and streamable HTTP
- Connector support: PostgreSQL, MySQL, SQLite, MongoDB
- Safe defaults: read_only Mode, explicit write allow-list
- Policy Caps: timeout, row limit, payload size
- Audit Entry chain for who/when/what/outcome

## Security first

- OWASP A01: default deny by Operation Class
- OWASP A03: parameterized SQL and validated Mongo filters
- OWASP A05: unsafe settings are called out in docs and examples
- NIST AU-2/AU-3: structured audit events for every Tool invocation

## Start here

1. [Install](install.md)
2. [Quickstart](quickstart.md)
3. [Architecture](architecture.md)
4. [Security Model](security-model.md)

## Example stacks

- `examples/01-minimal/README.md`: local SQLite and stdio
- `examples/02-prod-http-oauth/README.md`: HTTP transport with bearer auth
- `examples/03-multimodal-audit/README.md`: multi-backend with audit chain checks
