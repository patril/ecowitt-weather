#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing. Copy .env.example to .env and edit it first."
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${DATA_ROOT:?DATA_ROOT must be set in .env}"

if ! mountpoint -q "$DATA_ROOT"; then
  echo "ERROR: $DATA_ROOT is not mounted."
  echo "Refusing to start, because Docker would otherwise write database data to the microSD card."
  exit 1
fi

docker compose up -d --build
