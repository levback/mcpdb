# Mutation Testing

This directory contains the mutation-testing configuration for `mcpdb`.

## Run

```bash
uv run mutmut run --paths-to-mutate src/mcpdb/db src/mcpdb/server
```

## Report

```bash
uv run mutmut results
```

## Gate

- Target kill ratio: `>=75%`
- Scope: `src/mcpdb/db` and `src/mcpdb/server`
- OWASP A04: mutation survivors are treated as design-test gaps.

## Notes

- Run on a warm cache for stable timing.
- Keep the mutation run separate from the mandatory gate chain unless explicitly requested.
