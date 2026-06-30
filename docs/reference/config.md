# Config reference

This is the narrative companion for [config.schema.json](config.schema.json).

## Top-level keys

- `profiles`: list of database Profile definitions
- `limits`: global Cap values
- `security`: auth and network controls

## Profile fields

- `name`: unique profile name used by Tools and Resources
- `backend`: one of `postgres`, `mysql`, `sqlite`, `mongodb`
- `mode`: `read_only` or `read_write`
- connection fields: `host`/`port`/`database` or `dsn`

## SecretRef

Use references such as `${env:PG_PASSWORD}` instead of plaintext secrets.

## Security defaults

- Mode defaults to read-only
- binds should remain loopback in local development
- HTTP auth should stay enabled in networked deployments # OWASP A05

## Validation behavior

`mcpdb config validate` enforces type checks, uniqueness constraints, and limit bounds.
