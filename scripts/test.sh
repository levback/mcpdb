#!/usr/bin/env sh
set -eu

uv sync --all-extras --dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src --strict
uv run bandit -r src -lll
uv run pytest --cov=mcpdb --cov-branch --cov-fail-under=90 -q
uv run python -m mcpdb.cli --help