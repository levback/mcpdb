# CLI usage

## Global help

```bash
uv run python -m mcpdb.cli --help
```

## Serve

### stdio

```bash
uv run python -m mcpdb.cli serve --transport stdio --config examples/01-minimal/mcpdb.yaml
```

### HTTP

```bash
uv run python -m mcpdb.cli serve --transport http --host 127.0.0.1 --port 8080 --config examples/02-prod-http-oauth/mcpdb.yaml
```

## Config validation

```bash
uv run python -m mcpdb.cli config validate --file examples/config/minimal.yaml
```

## Doctor

```bash
uv run python -m mcpdb.cli doctor
```

## Audit command

```bash
uv run python -m mcpdb.cli audit --help
```

## REPL

```bash
uv run python -m mcpdb.cli repl --help
```

## Expected exit behavior

- exit 0 for valid command and configuration
- non-zero for validation or runtime failures
