#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${1:-/mnt/weather-data}"

if ! mountpoint -q "$DATA_ROOT"; then
  echo "ERROR: $DATA_ROOT is not a mounted filesystem."
  echo "Mount the USB/thumb drive there before creating Docker data directories."
  exit 1
fi

sudo mkdir -p "$DATA_ROOT/postgres" "$DATA_ROOT/grafana"

# Official postgres image runs as uid/gid 999. Grafana runs as uid/gid 472.
sudo chown -R 999:999 "$DATA_ROOT/postgres"
sudo chown -R 472:472 "$DATA_ROOT/grafana"

echo "Prepared persistent data directories under $DATA_ROOT"
