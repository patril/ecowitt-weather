import json
import os
import time
from datetime import datetime, timezone

import psycopg
import requests

USE_MOCK_GW3000 = os.environ.get("USE_MOCK_GW3000", "false").strip().lower() in {"1", "true", "yes", "on"}
ECOWITT_REAL_URL = os.environ.get("ECOWITT_REAL_URL", "http://192.168.4.131/get_livedata_info")
MOCK_GW3000_URL = os.environ.get("MOCK_GW3000_URL", "http://mock-gw3000:8080/get_livedata_info")
ECOWITT_URL = MOCK_GW3000_URL if USE_MOCK_GW3000 else ECOWITT_REAL_URL
DATABASE_URL = os.environ["DATABASE_URL"]
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "30"))


def first_number(value):
    """Return the first numeric token from values such as '5.82 mph' or '81%'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    token = str(value).strip().replace("%", "").split()[0]
    try:
        return float(token)
    except (ValueError, TypeError, IndexError):
        return None


def as_int(value):
    number = first_number(value)
    return int(number) if number is not None else None


def index_by_id(items):
    return {str(item.get("id")): item for item in (items or []) if "id" in item}


def item_value(items_by_id, item_id):
    item = items_by_id.get(item_id)
    return first_number(item.get("val")) if item else None


def parse_local_timestamp(value):
    if not value:
        return None
    # GW3000 `date` currently returns ISO-like local station time without an offset.
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_weather(payload, observed_at):
    common = index_by_id(payload.get("common_list"))
    wh25 = (payload.get("wh25") or [{}])[0]

    return {
        "observed_at": observed_at,
        "outdoor_temp_f": item_value(common, "0x02"),
        "outdoor_humidity_pct": item_value(common, "0x07"),
        # Ecowitt emits id "3" (without 0x) as the feels-like value in this payload.
        "feels_like_f": item_value(common, "3"),
        "dewpoint_f": item_value(common, "0x03"),
        "wind_speed_mph": item_value(common, "0x0B"),
        "wind_gust_mph": item_value(common, "0x0C"),
        "daily_max_wind_mph": item_value(common, "0x19"),
        "wind_direction_deg": item_value(common, "0x0A"),
        "solar_w_m2": item_value(common, "0x15"),
        "uv_index": item_value(common, "0x17"),
        "indoor_temp_f": first_number(wh25.get("intemp")),
        "indoor_humidity_pct": first_number(wh25.get("inhumi")),
        "absolute_pressure_inhg": first_number(wh25.get("abs")),
        "relative_pressure_inhg": first_number(wh25.get("rel")),
        "raw_json": json.dumps(payload),
    }


def parse_rain_group(items, observed_at, source):
    by_id = index_by_id(items)
    year_item = by_id.get("0x13", {})

    # 0x7C/0x7D appear in the current device payload but are not assigned here
    # until their semantics are confirmed. They remain preserved in raw_json.
    return {
        "observed_at": observed_at,
        "source": source,
        "event_rain_in": item_value(by_id, "0x0D"),
        "rain_rate_in_hr": item_value(by_id, "0x0E"),
        "daily_rain_in": item_value(by_id, "0x10"),
        "weekly_rain_in": item_value(by_id, "0x11"),
        "monthly_rain_in": item_value(by_id, "0x12"),
        "yearly_rain_in": item_value(by_id, "0x13"),
        "battery_level": as_int(year_item.get("battery")),
        "battery_voltage_v": first_number(year_item.get("voltage")),
        "ws90_cap_voltage_v": first_number(year_item.get("ws90cap_volt")),
        "ws90_firmware": year_item.get("ws90_ver"),
        "raw_json": json.dumps(items),
    }


def parse_lightning(payload, observed_at):
    item = (payload.get("lightning") or [{}])[0]
    if not item:
        return None
    return {
        "observed_at": observed_at,
        "last_strike_at_local": parse_local_timestamp(item.get("date")),
        "distance_miles": first_number(item.get("distance")),
        "cumulative_count": as_int(item.get("count")),
        "battery_level": as_int(item.get("battery")),
        "raw_json": json.dumps(item),
    }


def insert_weather(cur, row):
    cur.execute(
        """
        INSERT INTO weather_observation (
            observed_at, outdoor_temp_f, outdoor_humidity_pct, feels_like_f,
            dewpoint_f, wind_speed_mph, wind_gust_mph, daily_max_wind_mph,
            wind_direction_deg, solar_w_m2, uv_index, indoor_temp_f,
            indoor_humidity_pct, absolute_pressure_inhg, relative_pressure_inhg,
            raw_json
        ) VALUES (
            %(observed_at)s, %(outdoor_temp_f)s, %(outdoor_humidity_pct)s,
            %(feels_like_f)s, %(dewpoint_f)s, %(wind_speed_mph)s,
            %(wind_gust_mph)s, %(daily_max_wind_mph)s,
            %(wind_direction_deg)s, %(solar_w_m2)s, %(uv_index)s,
            %(indoor_temp_f)s, %(indoor_humidity_pct)s,
            %(absolute_pressure_inhg)s, %(relative_pressure_inhg)s,
            %(raw_json)s::jsonb
        )
        """,
        row,
    )


def insert_rain(cur, row):
    cur.execute(
        """
        INSERT INTO rain_observation (
            observed_at, source, event_rain_in, rain_rate_in_hr,
            daily_rain_in, weekly_rain_in, monthly_rain_in, yearly_rain_in,
            battery_level, battery_voltage_v, ws90_cap_voltage_v,
            ws90_firmware, raw_json
        ) VALUES (
            %(observed_at)s, %(source)s, %(event_rain_in)s, %(rain_rate_in_hr)s,
            %(daily_rain_in)s, %(weekly_rain_in)s, %(monthly_rain_in)s,
            %(yearly_rain_in)s, %(battery_level)s, %(battery_voltage_v)s,
            %(ws90_cap_voltage_v)s, %(ws90_firmware)s, %(raw_json)s::jsonb
        )
        """,
        row,
    )


def insert_lightning(cur, row):
    if row is None:
        return
    cur.execute(
        """
        INSERT INTO lightning_observation (
            observed_at, last_strike_at_local, distance_miles,
            cumulative_count, battery_level, raw_json
        ) VALUES (
            %(observed_at)s, %(last_strike_at_local)s, %(distance_miles)s,
            %(cumulative_count)s, %(battery_level)s, %(raw_json)s::jsonb
        )
        """,
        row,
    )


def collect_once():
    response = requests.get(ECOWITT_URL, timeout=10)
    response.raise_for_status()
    payload = response.json()
    observed_at = datetime.now(timezone.utc)

    weather = parse_weather(payload, observed_at)
    rain_wh40 = parse_rain_group(payload.get("rain") or [], observed_at, "wh40")
    rain_ws90 = parse_rain_group(payload.get("piezoRain") or [], observed_at, "ws90")
    lightning = parse_lightning(payload, observed_at)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            insert_weather(cur, weather)
            if payload.get("rain"):
                insert_rain(cur, rain_wh40)
            if payload.get("piezoRain"):
                insert_rain(cur, rain_ws90)
            insert_lightning(cur, lightning)
        conn.commit()

    print(
        f"Stored observation {observed_at.isoformat()} "
        f"temp={weather['outdoor_temp_f']}F solar={weather['solar_w_m2']}W/m2",
        flush=True,
    )


def main():
    print(f"GW3000 source={'mock' if USE_MOCK_GW3000 else 'real'} url={ECOWITT_URL} poll={POLL_SECONDS}s", flush=True)
    while True:
        started = time.monotonic()
        try:
            collect_once()
        except Exception as exc:
            print(f"Collector error: {type(exc).__name__}: {exc}", flush=True)
        elapsed = time.monotonic() - started
        time.sleep(max(0, POLL_SECONDS - elapsed))


if __name__ == "__main__":
    main()
