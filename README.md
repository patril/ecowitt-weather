# Ecowitt Weather Stack

A small Raspberry Pi weather-data stack for the Ecowitt GW3000:

- Raspberry Pi OS + Docker on the **microSD card**
- PostgreSQL and Grafana persistent data on a **USB/thumb drive**
- Python collector polling the GW3000 local HTTP API
- Grafana automatically provisioned with PostgreSQL as its default datasource

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

```bash
cp .env.example .env
```

The sample is already set to the GW3000 address observed during development:

```text
ECOWITT_URL=http://192.168.4.131/get_livedata_info
```

Keep that address reserved in Eero, and change the two example passwords in `.env`.

## 3. Prepare USB directories

After the drive is mounted:

```bash
./scripts/prepare-usb.sh
```

This creates the PostgreSQL and Grafana directories and sets the ownership expected by their
containers.

## 4. Start the stack

Use the guarded start script:

```bash
./scripts/start.sh
```

Or, after verifying the drive is mounted yourself:

```bash
docker compose up -d --build
```

Grafana will be available at:

```text
http://<raspberry-pi-ip>:3000
```

PostgreSQL is intentionally **not exposed to the LAN**. Grafana and the collector reach it over
the private Docker Compose network.

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

## First-run schema behavior

SQL files under `postgres/init/` run automatically only when PostgreSQL initializes an empty data
directory. That is appropriate for a new thumb drive. Future schema changes should be handled as
migrations rather than by editing the initial schema and expecting an existing database to change.

## Raspberry Pi 4 Model B (2 GB)

The initial target is a Raspberry Pi 4 Model B with 2 GB RAM. This is sufficient for this low-volume weather workload. PostgreSQL is configured with a modest 64 MB `shared_buffers` setting to keep the stack comfortable on 2 GB. The storage design deliberately keeps the persistent data independent of the Pi hardware, so a later Pi upgrade does not require redesigning the application.

## Real vs. mock GW3000

The Compose stack includes `mock-gw3000`, a tiny Python HTTP service that implements `/get_livedata_info` using the same JSON shape observed from the physical GW3000. It generates gently changing temperature, wind, solar and related values so Grafana charts continue to move during development.

Choose the source in `.env`:

```text
USE_MOCK_GW3000=false
ECOWITT_REAL_URL=http://192.168.4.131/get_livedata_info
```

Use the physical station while on the home LAN. Away from home, change only:

```text
USE_MOCK_GW3000=true
```

and restart the collector:

```bash
docker compose up -d --build collector mock-gw3000
```

The mock is also published to the host at port 8080, so it can be inspected directly:

```bash
curl http://localhost:8080/get_livedata_info
```

Inside Docker, the collector always reaches the mock as `http://mock-gw3000:8080/get_livedata_info`; no host networking trickery is required.
