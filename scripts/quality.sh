#!/usr/bin/env sh
set -eu

mode="${1:-all}"

run_properties() {
  uv run pytest tests/properties -q
}

run_fuzz_smoke() {
  uv run pytest tests/fuzz/fuzz_jsonrpc.py tests/fuzz/fuzz_config.py -q
}

run_chaos() {
  uv run pytest tests/chaos -q
}

run_mutation() {
  uv run mutmut run --paths-to-mutate src/mcpdb/db src/mcpdb/server
  uv run mutmut results
}

case "$mode" in
  properties)
    run_properties
    ;;
  fuzz)
    run_fuzz_smoke
    ;;
  chaos)
    run_chaos
    ;;
  mutation)
    run_mutation
    ;;
  all)
    run_properties
    run_fuzz_smoke
    run_chaos
    ;;
  *)
    echo "usage: scripts/quality.sh [properties|fuzz|chaos|mutation|all]"
    exit 2
    ;;
esac
