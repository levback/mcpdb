# Example 01: Minimal SQLite

## Run

```bash
docker compose up --build
```

## Validate config

```bash
uv run python -m mcpdb.cli config validate --file mcpdb.yaml
```

This stack is local-only and defaults to read-only Mode.
