# CLI Usage

## Overview

The mcpdb CLI provides operational commands for running and validating the server:

- serve
- doctor
- config validate
- config schema
- tools
- profiles
- repl
- audit

## Global Options

- --config PATH: explicit config file path
- --log-level LEVEL: logger verbosity
- --version: print version and build commit

## Commands

### serve

Run server transport:

- stdio transport: default
- http transport: requires auth-enabled config

Example:

```bash
mcpdb serve --transport http --bind 127.0.0.1 --port 8765
```

Security behavior:

- bind 0.0.0.0 is rejected when auth is disabled.

### doctor

Run a health audit for configured profiles:

- validates config loading
- checks backend reachability via ping
- returns exit code 0 when all checks pass
- returns exit code 1 when any check fails

Example:

```bash
mcpdb doctor --config examples/config/minimal.yaml
```

### config validate

Validate config file and SecretRef resolution.

Exit codes:

- 0: valid
- 1: validation failure
- 2: malformed YAML

Example:

```bash
mcpdb config validate examples/config/minimal.yaml
```

### config schema

Print JSON schema for configuration model to stdout.

Example:

```bash
mcpdb config schema > docs/reference/config.schema.json
```

### tools

List MCP Tool names registered for current profile set.

Example:

```bash
mcpdb tools list
```

### profiles

List configured profiles and Backends.

Example:

```bash
mcpdb profiles list
```

### repl

Start interactive REPL command mode.

Supported slash commands:

- /help
- /profiles
- /tools
- /ping <profile>
- /query <profile> <statement>
- /exit

### audit

Verify HMAC chain integrity for audit JSONL file.

Exit codes:

- 0: valid chain
- 2: tampered chain
- 3: malformed file or missing file

Example:

```bash
mcpdb audit verify audit.log --key test-key
```

## Environment Variables

- MCPDB_BUILD_COMMIT: build metadata shown in --version output
- MCPDB__* nested config overrides, applied with double-underscore keys

## Completion

Generate shell completion with built-in Typer support:

```bash
mcpdb --install-completion zsh
```

Supported shells include bash, zsh, and fish.
