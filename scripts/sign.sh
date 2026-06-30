#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/sign.sh <artifact> [<artifact> ...]" >&2
  exit 2
fi

if ! command -v cosign >/dev/null 2>&1; then
  echo "cosign is required for signing" >&2
  exit 1
fi

mkdir -p attestations

for artifact in "$@"; do
  if [ ! -f "$artifact" ]; then
    echo "artifact not found: $artifact" >&2
    exit 1
  fi

  bundle="attestations/$(basename "$artifact").bundle.json"
  # OWASP A08: sign each release artifact with keyless OIDC identity.
  cosign sign-blob \
    --yes \
    --bundle "$bundle" \
    "$artifact"

done
