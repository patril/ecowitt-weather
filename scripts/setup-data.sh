#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${DATA_ROOT:-./data}"

echo "Preparing persistent data at: $DATA_ROOT"

mkdir -p "$DATA_ROOT/postgres"
mkdir -p "$DATA_ROOT/grafana"

# Determine the UID/GID actually used by the selected Postgres image.
POSTGRES_UID="$(docker run --rm --entrypoint sh postgres:16 \
    -c 'id -u postgres')"
POSTGRES_GID="$(docker run --rm --entrypoint sh postgres:16 \
    -c 'id -g postgres')"

echo "PostgreSQL UID:GID = ${POSTGRES_UID}:${POSTGRES_GID}"
echo "Grafana UID:GID    = 472:0"

sudo chown -R "${POSTGRES_UID}:${POSTGRES_GID}" \
    "$DATA_ROOT/postgres"

sudo chown -R 472:0 \
    "$DATA_ROOT/grafana"

sudo chmod 700 "$DATA_ROOT/postgres"
sudo chmod 775 "$DATA_ROOT/grafana"

echo
echo "Persistent directories:"
ls -ld "$DATA_ROOT/postgres" "$DATA_ROOT/grafana"

echo
echo "Setup complete."