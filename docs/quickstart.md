# Quickstart (5 minutes)

This quickstart uses the minimal SQLite Profile in read_only Mode.

## 1) Bootstrap dev environment

```bash
./scripts/bootstrap.sh
```

## 2) Validate config

```bash
uv run python -m mcpdb.cli config validate --file examples/01-minimal/mcpdb.yaml
```

## 3) Run stdio transport

```bash
uv run python -m mcpdb.cli serve --transport stdio --config examples/01-minimal/mcpdb.yaml
```

## 4) Claude Desktop configuration

Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcpdb": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "mcpdb.cli",
        "serve",
        "--transport",
        "stdio",
        "--config",
        "examples/01-minimal/mcpdb.yaml"
      ]
    }
  }
}
```

## 5) Ask your client to call tools

- `db_query` for read queries
- `db_introspect` for metadata

All calls enforce Policy Caps and emit an Audit Entry.

## Expected behavior

- READ operations are allowed.
- WRITE operations are denied unless Mode is `read_write` and Policy allows writes.
- SQL must be parameterized; ad-hoc injected SQL is rejected. # OWASP A03
