from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Mapping
from zoneinfo import ZoneInfo
import os
import psycopg

if TYPE_CHECKING:
    from daily_energy import DailyEnergyResult
    from dto.IrradianceReading import IrradianceReading

DATABASE_URL = os.environ["DATABASE_URL"]
STATION_TIMEZONE = ZoneInfo(os.environ.get("STATION_TIMEZONE", "America/New_York"))


def _insert(sql: str, row: Mapping[str, object]) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, row)
        conn.commit()


def station_day_bounds(observation_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(observation_date, time.min, tzinfo=STATION_TIMEZONE)
    end = datetime.combine(observation_date + timedelta(days=1), time.min, tzinfo=STATION_TIMEZONE)
    return start, end


def get_irradiance_readings(observation_date: date) -> list[IrradianceReading]:
    from dto.IrradianceReading import IrradianceReading

    start, end = station_day_bounds(observation_date)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT observed_at, solar_w_m2
                FROM weather_observation
                WHERE observed_at >= %s
                  AND observed_at < %s
                  AND solar_w_m2 IS NOT NULL
                ORDER BY observed_at ASC
                """,
                (start, end),
            )
            return [
                IrradianceReading(observed_at=row[0], irradiance=row[1])
                for row in cur.fetchall()
            ]


def upsert_daily_solar_energy(result: DailyEnergyResult) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO daily_solar_energy (
                    observation_date, energy_wh_m2, sample_count, gap_count,
                    max_gap_seconds, is_complete, calculated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (observation_date) DO UPDATE SET
                    energy_wh_m2 = EXCLUDED.energy_wh_m2,
                    sample_count = EXCLUDED.sample_count,
                    gap_count = EXCLUDED.gap_count,
                    max_gap_seconds = EXCLUDED.max_gap_seconds,
                    is_complete = EXCLUDED.is_complete,
                    calculated_at = NOW()
                """,
                (
                    result.observation_date,
                    result.energy_wh_m2,
                    result.sample_count,
                    result.gap_count,
                    result.max_gap_seconds,
                    result.is_complete,
                ),
            )
        conn.commit()


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
