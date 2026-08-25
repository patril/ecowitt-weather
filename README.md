# Ecowitt Weather Stack

A small Raspberry Pi weather-data stack for the Ecowitt GW3000:

- Raspberry Pi OS + Docker on the **microSD card**
- PostgreSQL and Grafana persistent data on a **USB/thumb drive**
- Python collector polling the GW3000 local HTTP API
- Grafana automatically provisioned with PostgreSQL as its default datasource
- Daily solar-energy integration from stored irradiance observations

## Hardware/storage layout

```text
Raspberry Pi 4
├── microSD
│   ├── Raspberry Pi OS
│   ├── Docker / Compose
│   └── this project
│
└── USB 3 thumb drive (ext4)
    └── /mnt/weather-data
        ├── postgres/
        └── grafana/
```

The Compose project uses bind mounts rather than Docker named volumes. The `scripts/start.sh`
wrapper refuses to start if `/mnt/weather-data` is not actually mounted, preventing a failed
USB mount from silently putting PostgreSQL data onto the microSD card.

## 1. Mount the thumb drive permanently

Format the intended thumb drive as ext4, then find its UUID:

```bash
lsblk -f
```

Create the mount point:

```bash
sudo mkdir -p /mnt/weather-data
```

Add an `/etc/fstab` entry using the drive's real UUID:

```text
UUID=YOUR-USB-UUID /mnt/weather-data ext4 defaults,noatime,nofail,x-systemd.device-timeout=10 0 2
```

Then:

```bash
sudo mount -a
findmnt /mnt/weather-data
```

`findmnt` should show the USB drive as the source for `/mnt/weather-data`.

> `nofail` allows the Pi itself to boot if the USB drive is absent. The supplied start script
> still refuses to launch the weather stack until the drive is mounted.

## 2. Configure the project

Create `.env` and set at least the passwords and data root. The real GW3000 URL observed during development is:

```text
DATA_ROOT=/mnt/weather-data
ECOWITT_REAL_URL=http://192.168.4.131/get_livedata_info
STATION_TIMEZONE=America/New_York
USE_MOCK_GW3000=false
```

Keep the GW3000 address reserved in Eero. On a development machine, `DATA_ROOT=./data` is convenient.

## 3. Prepare persistent directories

After the USB drive is mounted on the Pi:

```bash
./scripts/prepare-usb.sh
```

For development, `scripts/setup-data.sh` prepares the configured `DATA_ROOT` with the ownership expected by PostgreSQL and Grafana.

## 4. Start the stack

Use the guarded start script on the Pi:

```bash
./scripts/start.sh
```

Or, after verifying storage yourself:

```bash
docker compose up -d --build
```

Grafana is published on host port `3001`. PostgreSQL is intentionally **not exposed to the LAN**. Grafana and the collector reach it over the private Docker Compose network.

## Database schema

### `weather_observation`

Stores the main WS90/GW3000 observations, including outdoor temperature/humidity, feels-like,
dew point, wind speed/gust/direction, daily maximum wind, solar radiation, UV, indoor readings,
and barometric pressure. The complete GW3000 payload is also retained in `raw_json`.

### `rain_observation`

Stores WH40 tipping-bucket (`source='wh40'`) and WS90 piezo (`source='ws90'`) readings separately:
event rain, rain rate, daily/weekly/monthly/yearly totals, battery information, and WS90 diagnostic
voltage/firmware fields when present.

The GW3000 response currently also contains rain IDs `0x7C` and `0x7D`. They are deliberately not
assigned semantic columns yet; the values remain preserved in `raw_json` until their definitions
are confirmed.

### `lightning_observation`

Stores the WH57's most recently reported strike time, distance, cumulative count, and battery level.
The gateway's strike time has no timezone offset, so it is stored as a PostgreSQL `TIMESTAMP`
(local station time) rather than pretending it is UTC.

### `daily_solar_energy`

Stores the trapezoidal integration of each station-local day's irradiance readings. `energy_wh_m2` is in Wh/m²; divide by 1000 for kWh/m²/day. The row also stores sample count, detected sampling gaps, the largest gap, a completeness flag, and calculation time.

Intervals longer than the configured maximum gap (five minutes by default) are **not** interpolated. The partial energy is retained, but `is_complete=false`, so missing data cannot silently masquerade as a precise daily total.

The date query uses half-open timestamp bounds in `STATION_TIMEZONE` (default `America/New_York`), including correct 23- and 25-hour DST days.

## Daily energy job

Calculate and upsert yesterday's value manually:

```bash
bash scripts/calculate-yesterday.sh
```

Or calculate a specific date:

```bash
docker compose run --rm --no-deps collector python daily_energy_job.py 2026-08-25
```

The upsert is idempotent, so recalculating a date safely replaces its previous result. A simple host cron schedule is sufficient. For example, run yesterday shortly after midnight and again at 03:00 as a recovery run:

```cron
5 0 * * * cd /home/patrick/ecowitt-weather && /bin/bash scripts/calculate-yesterday.sh >> /var/log/ecowitt-daily-energy.log 2>&1
0 3 * * * cd /home/patrick/ecowitt-weather && /bin/bash scripts/calculate-yesterday.sh >> /var/log/ecowitt-daily-energy.log 2>&1
```

Adjust the project path and log destination for the Pi. Cron should run as a user that can access Docker.

## Schema migrations

SQL files under `postgres/init/` run automatically only when PostgreSQL initializes an empty data directory. For an existing database, apply the idempotent schema files with:

```bash
bash scripts/run-migrations.sh
```

Run this after pulling a version that adds a migration and before running code that depends on the new schema.

## Tests

The daily integration tests use Python's standard `unittest` module:

```bash
docker compose run --rm --no-deps collector python -m unittest test_daily_energy.py
```

They cover units, irregular sampling, missing-data gaps, empty/single-reading days, and station-local DST boundaries.

## Useful commands

```bash
# Confirm USB storage is mounted
findmnt /mnt/weather-data

# See service status
docker compose ps

# Follow collector output
docker compose logs -f collector

# Stop the stack
docker compose down
```

## Raspberry Pi 4 Model B (2 GB)

The initial target is a Raspberry Pi 4 Model B with 2 GB RAM. This is sufficient for this low-volume weather workload. PostgreSQL is configured with a modest 64 MB `shared_buffers` setting to keep the stack comfortable on 2 GB. The storage design deliberately keeps the persistent data independent of the Pi hardware, so a later Pi upgrade does not require redesigning the application.

## Real vs. mock GW3000

The Compose stack includes `mock-gw3000`, a tiny Python HTTP service that implements `/get_livedata_info` using the same JSON shape observed from the physical GW3000. It generates gently changing temperature, wind, solar and related values so Grafana charts continue to move during development.

Choose the source in `.env`:

```text
USE_MOCK_GW3000=false
ECOWITT_REAL_URL=http://192.168.4.131/get_livedata_info
```

Away from home, change only:

```text
USE_MOCK_GW3000=true
```

and restart the collector:

```bash
docker compose up -d --build collector mock-gw3000
```

The mock is published to the host at port `8081`, so it can be inspected directly:

```bash
curl http://localhost:8081/get_livedata_info
```

Inside Docker, the collector reaches the mock as `http://mock-gw3000:8080/get_livedata_info`; no host networking trickery is required.
