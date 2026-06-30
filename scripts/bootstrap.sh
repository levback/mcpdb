#!/usr/bin/env sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  uv venv
fi

uv sync --all-extras --dev
uv run pre-commit install

if [ ! -f "mcpdb.yaml" ]; then
  cp examples/01-minimal/mcpdb.yaml mcpdb.yaml
fi

echo "bootstrap complete"
