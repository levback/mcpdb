#!/usr/bin/env sh
set -eu

uv run bandit -r src -lll
uv run pip-audit

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "gitleaks is required to run the full security scan"
  exit 1
fi

gitleaks detect --source .