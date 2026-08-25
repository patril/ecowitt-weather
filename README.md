# Ecowitt Weather Stack

A small Raspberry Pi weather-data stack for the Ecowitt GW3000:

- Raspberry Pi OS + Docker on the **microSD card**
- PostgreSQL and Grafana persistent data on a **USB/thumb drive**
- Python collector polling the GW3000 local HTTP API
- Mock GW3000 service for off-network development
- Grafana automatically provisioned with PostgreSQL as its default datasource
- Source-controlled Grafana weather dashboard provisioned automatically at startup
- nginx reverse proxy publishing the dashboard at `http://weather.local/`
- Daily solar-energy integration from stored irradiance observations
- Containerized cron scheduler for daily solar-energy calculations

## Hardware/storage layout

```text
Raspberry Pi 4 Model B (2 GB)
├── microSD
│   ├── Raspberry Pi OS 64-bit
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

The initial target is a Raspberry Pi 4 Model B with 2 GB RAM. PostgreSQL is configured with a modest
64 MB `shared_buffers` setting. This is enough for the expected weather workload, and the persistent
storage is independent of the Pi so the computer can be replaced later without redesigning the stack.

## Laptop development

On a development machine, use a normal local directory for persistent data rather than pretending
that the Pi's USB mount exists:

```text
DATA_ROOT=./data
USE_MOCK_GW3000=true
STATION_TIMEZONE=America/New_York
```

Prepare the bind-mounted directories:

```bash
./scripts/setup-data.sh
```

Then start the stack:

```bash
docker compose up -d --build
```

The mock GW3000 is published at:

```bash
curl http://localhost:8081/get_livedata_info
```

Grafana is served through nginx on host port 80. The production hostname is `weather.local`.
For local development, add a temporary hosts-file entry for `weather.local` pointing at the development machine if needed.

When testing against the physical gateway while on the home LAN, set:

```text
USE_MOCK_GW3000=false
ECOWITT_REAL_URL=http://192.168.4.131/get_livedata_info
```

The GW3000 address should remain reserved in Eero.

## Raspberry Pi deployment

The Pi deployment is intentionally straightforward: the microSD contains replaceable software;
the USB drive contains the persistent database and Grafana state.

### 1. Install Raspberry Pi OS

Use **64-bit Raspberry Pi OS Lite** on the microSD card. The Pi is a headless server, so the desktop
environment is unnecessary. Enable SSH during imaging if you want to administer it remotely.

After the first boot:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Set the Pi hostname so mDNS advertises it as `weather.local`:

```bash
sudo hostnamectl set-hostname weather
sudo reboot
```

Verify after reboot:

```bash
hostname
systemctl status avahi-daemon
```

Set and verify the station timezone:

```bash
sudo timedatectl set-timezone America/New_York
timedatectl
```

### 2. Install Docker Engine and Compose

Use Docker Engine with the Compose plugin rather than the Snap package. For 64-bit Raspberry Pi OS,
Docker's supported Debian `arm64` installation is appropriate. Follow Docker's current Debian
installation instructions, then verify:

```bash
docker --version
docker compose version
sudo systemctl status docker
```

If you choose to run Docker without `sudo`, add your user to the `docker` group and log out/back in:

```bash
sudo usermod -aG docker "$USER"
```

> Membership in the `docker` group effectively grants root-level control of the host. On this
> dedicated Pi that is a deliberate administrative choice.

### 3. Clone the project

For example:

```bash
cd ~
git clone https://github.com/patril/ecowitt-weather.git
cd ecowitt-weather
```

### 4. Mount the USB data drive permanently

Format the intended USB drive as ext4, then find its UUID:

```bash
lsblk -f
```

Create the mount point:

```bash
sudo mkdir -p /mnt/weather-data
```

Add an `/etc/fstab` entry using the drive's actual UUID:

```text
UUID=YOUR-USB-UUID /mnt/weather-data ext4 defaults,noatime,nofail,x-systemd.device-timeout=10 0 2
```

Then verify the mount:

```bash
sudo mount -a
findmnt /mnt/weather-data
```

`findmnt` should show the USB device as the source for `/mnt/weather-data`.

`nofail` lets the Pi itself boot if the USB drive is absent. The supplied `scripts/start.sh` still
refuses to launch the weather stack until `/mnt/weather-data` is really mounted.

### 5. Configure `.env` for the Pi

Create `.env` in the project directory. At minimum configure the data root, passwords, station URL,
and timezone:

```text
DATA_ROOT=/mnt/weather-data
POSTGRES_DB=weather
POSTGRES_USER=weather
POSTGRES_PASSWORD=CHOOSE_A_PASSWORD
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=CHOOSE_A_DIFFERENT_PASSWORD
USE_MOCK_GW3000=false
ECOWITT_REAL_URL=http://192.168.4.131/get_livedata_info
STATION_TIMEZONE=America/New_York
POLL_SECONDS=30
DAILY_ENERGY_MAX_GAP_SECONDS=300
```

Do not commit `.env`.

### 6. Prepare the persistent directories

After the USB drive is mounted:

```bash
./scripts/prepare-usb.sh
```

This creates the PostgreSQL and Grafana directories with the ownership expected by their containers.

### 7. Start the stack

Use the guarded start script:

```bash
./scripts/start.sh
```

Then verify all services:

```bash
docker compose ps
```

You should see PostgreSQL, the collector, Grafana, nginx, the mock service, and the daily-energy scheduler.
The mock remains running but is ignored when `USE_MOCK_GW3000=false`.

Useful logs:

```bash
docker compose logs -f collector
docker compose logs -f daily-energy-scheduler
docker compose logs -f nginx
```

Browse to:

```text
http://weather.local/
```

nginx is the only dashboard-facing service published to the LAN. Grafana listens on port 3000 only
inside the private Compose network, and PostgreSQL is also intentionally **not exposed to the LAN**.

### 8. First database initialization vs. later upgrades

On a brand-new USB data directory, PostgreSQL automatically runs the SQL files under
`postgres/init/` when it initializes the database.

When updating an existing installation after pulling a version that adds a schema migration, run:

```bash
bash scripts/run-migrations.sh
```

Do this before running code that depends on the new schema.

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

Stores the trapezoidal integration of each station-local day's irradiance readings. `energy_wh_m2`
is in Wh/m²; divide by 1000 for kWh/m²/day. The row also stores sample count, detected sampling gaps,
the largest gap, a completeness flag, and calculation time.

Intervals longer than the configured maximum gap (five minutes by default) are **not** interpolated.
The partial energy is retained, but `is_complete=false`, so missing data cannot silently masquerade
as a precise daily total.

The date query uses half-open timestamp bounds in `STATION_TIMEZONE` (default `America/New_York`),
including correct 23- and 25-hour DST days.

## Containerized daily-energy schedule

No host crontab is required. `docker-compose.yml` includes a `daily-energy-scheduler` service built
from the same Python source as the collector. The image contains Debian cron, and cron runs in the
foreground as the container's main process.

The scheduler calculates **yesterday** twice each station-local night:

```text
00:05  primary calculation
03:00  recovery/recalculation
```

The second run is intentional. The database write is an upsert, so recalculation is harmless, while
a brief reboot or database outage around midnight is less likely to leave a missing day.

The scheduler uses `STATION_TIMEZONE`, so the schedule follows local Eastern time including DST.
The default maximum accepted sampling gap is 300 seconds and can be changed in `.env`:

```text
DAILY_ENERGY_MAX_GAP_SECONDS=300
```

Inspect scheduler activity with:

```bash
docker compose logs daily-energy-scheduler
```

Calculate and upsert yesterday manually at any time:

```bash
bash scripts/calculate-yesterday.sh
```

Or calculate a specific station-local date:

```bash
docker compose run --rm --no-deps collector python daily_energy_job.py 2026-08-25
```

## Tests

The daily integration tests use Python's standard `unittest` module:

```bash
docker compose run --rm --no-deps collector python -m unittest test_daily_energy.py
```

They cover units, irregular sampling, missing-data gaps, empty/single-reading days, and station-local
DST boundaries.

## Useful commands

```bash
# See service status
docker compose ps

# Follow weather collection
docker compose logs -f collector

# Follow daily scheduler
docker compose logs -f daily-energy-scheduler

# Follow reverse proxy
docker compose logs -f nginx

# Confirm Pi USB storage is mounted
findmnt /mnt/weather-data

# Apply schema changes to an existing database
bash scripts/run-migrations.sh

# Stop the stack
docker compose down
```
