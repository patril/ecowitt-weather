from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Mapping
import os
import psycopg

if TYPE_CHECKING:
    from collector.dto.IrradianceReading import IrradianceReading

DATABASE_URL = os.environ["DATABASE_URL"]


def _insert(sql: str, row: Mapping[str, object]) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, row)
        conn.commit()


def get_irradiance_readings(date: date) -> list[IrradianceReading]:
    from collector.dto.IrradianceReading import IrradianceReading

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("select observed_at, solar_w_m2 from weather_observation where date_trunc('day', observed_at) = %s order by observed_at asc", (date,))
            return [IrradianceReading(observed_at=row[0], irradiance=row[1]) for row in cur.fetchall()]


def insert_weather(row: Mapping[str, object]) -> None:
    _insert(
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


def insert_rain(row: Mapping[str, object]) -> None:
    _insert(
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


def insert_lightning(row: Mapping[str, object] | None) -> None:
    if row is None:
        return
    _insert(
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
