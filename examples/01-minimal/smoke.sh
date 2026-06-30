#!/usr/bin/env sh
set -eu
uv run python -m mcpdb.cli config validate --file examples/01-minimal/mcpdb.yaml
