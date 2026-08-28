#!/bin/sh
set -eu

STATION_TIMEZONE="${STATION_TIMEZONE:-America/New_York}"
DAILY_ENERGY_MAX_GAP_SECONDS="${DAILY_ENERGY_MAX_GAP_SECONDS:-300}"
export TZ="$STATION_TIMEZONE"

python - <<'PY'
import os
import shlex

values = {
    "DATABASE_URL": os.environ["DATABASE_URL"],
    "STATION_TIMEZONE": os.environ.get("STATION_TIMEZONE", "America/New_York"),
    "DAILY_ENERGY_MAX_GAP_SECONDS": os.environ.get("DAILY_ENERGY_MAX_GAP_SECONDS", "300"),
}

with open("/run/ecowitt-cron.env", "w", encoding="utf-8") as env_file:
    for key, value in values.items():
        env_file.write(f"export {key}={shlex.quote(value)}\n")
PY

cat > /etc/cron.d/ecowitt-daily-jobs <<'EOF'
SHELL=/bin/sh
PATH=/usr/local/bin:/usr/bin:/bin

5 0 * * * root . /run/ecowitt-cron.env && cd /app && python daily_energy_job.py yesterday --max-gap-seconds "$DAILY_ENERGY_MAX_GAP_SECONDS" && python daily_wind_energy_job.py yesterday --max-gap-seconds "$DAILY_ENERGY_MAX_GAP_SECONDS" && python daily_weather_job.py yesterday >> /proc/1/fd/1 2>> /proc/1/fd/2
0 3 * * * root . /run/ecowitt-cron.env && cd /app && python daily_energy_job.py yesterday --max-gap-seconds "$DAILY_ENERGY_MAX_GAP_SECONDS" && python daily_wind_energy_job.py yesterday --max-gap-seconds "$DAILY_ENERGY_MAX_GAP_SECONDS" && python daily_weather_job.py yesterday >> /proc/1/fd/1 2>> /proc/1/fd/2
EOF

chmod 0644 /etc/cron.d/ecowitt-daily-jobs

echo "Daily schedulers enabled in ${STATION_TIMEZONE}: solar energy + wind energy + weather fingerprint at 00:05 and 03:00; max gap ${DAILY_ENERGY_MAX_GAP_SECONDS}s"
exec cron -f
