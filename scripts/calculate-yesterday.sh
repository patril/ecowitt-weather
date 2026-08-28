#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose run --rm --no-deps collector sh -c 'python daily_energy_job.py yesterday && python daily_wind_energy_job.py yesterday && python daily_weather_job.py yesterday'
