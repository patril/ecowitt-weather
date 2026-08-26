import argparse
from datetime import date, datetime, timedelta

import psycopg

from dao import DATABASE_URL, STATION_TIMEZONE, station_day_bounds


def parse_date(value: str) -> date:
    if value == "yesterday":
        return datetime.now(STATION_TIMEZONE).date() - timedelta(days=1)
    return date.fromisoformat(value)


def calculate_and_upsert(observation_date: date) -> None:
    start, end = station_day_bounds(observation_date)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH weather AS (
                    SELECT
                        MAX(outdoor_temp_f) AS high_temp_f,
                        MIN(outdoor_temp_f) AS low_temp_f,
                        AVG(dewpoint_f) AS mean_dewpoint_f,
                        MAX(wind_gust_mph) AS peak_gust_mph,
                        AVG(wind_speed_mph) AS mean_wind_mph,
                        MAX(solar_w_m2) AS peak_irradiance_w_m2,
                        AVG(relative_pressure_inhg) AS mean_relative_pressure_inhg,
                        COUNT(*)::integer AS sample_count
                    FROM weather_observation
                    WHERE observed_at >= %s AND observed_at < %s
                ),
                rain AS (
                    SELECT MAX(daily_rain_in) AS rainfall_in
                    FROM rain_observation
                    WHERE source = 'wh40'
                      AND observed_at >= %s AND observed_at < %s
                ),
                lightning AS (
                    SELECT
                        CASE
                            WHEN COUNT(cumulative_count) < 2 THEN 0
                            ELSE GREATEST(MAX(cumulative_count) - MIN(cumulative_count), 0)
                        END::integer AS lightning_strikes
                    FROM lightning_observation
                    WHERE observed_at >= %s AND observed_at < %s
                ),
                solar AS (
                    SELECT
                        energy_wh_m2 AS solar_energy_wh_m2,
                        is_complete AS solar_energy_is_complete
                    FROM daily_solar_energy
                    WHERE observation_date = %s
                )
                INSERT INTO daily_weather_summary (
                    observation_date,
                    high_temp_f,
                    low_temp_f,
                    mean_dewpoint_f,
                    rainfall_in,
                    peak_gust_mph,
                    mean_wind_mph,
                    peak_irradiance_w_m2,
                    solar_energy_wh_m2,
                    solar_energy_is_complete,
                    mean_relative_pressure_inhg,
                    lightning_strikes,
                    sample_count,
                    calculated_at
                )
                SELECT
                    %s,
                    weather.high_temp_f,
                    weather.low_temp_f,
                    weather.mean_dewpoint_f,
                    rain.rainfall_in,
                    weather.peak_gust_mph,
                    weather.mean_wind_mph,
                    weather.peak_irradiance_w_m2,
                    solar.solar_energy_wh_m2,
                    solar.solar_energy_is_complete,
                    weather.mean_relative_pressure_inhg,
                    lightning.lightning_strikes,
                    weather.sample_count,
                    NOW()
                FROM weather
                CROSS JOIN rain
                CROSS JOIN lightning
                LEFT JOIN solar ON TRUE
                WHERE weather.sample_count > 0
                ON CONFLICT (observation_date) DO UPDATE SET
                    high_temp_f = EXCLUDED.high_temp_f,
                    low_temp_f = EXCLUDED.low_temp_f,
                    mean_dewpoint_f = EXCLUDED.mean_dewpoint_f,
                    rainfall_in = EXCLUDED.rainfall_in,
                    peak_gust_mph = EXCLUDED.peak_gust_mph,
                    mean_wind_mph = EXCLUDED.mean_wind_mph,
                    peak_irradiance_w_m2 = EXCLUDED.peak_irradiance_w_m2,
                    solar_energy_wh_m2 = EXCLUDED.solar_energy_wh_m2,
                    solar_energy_is_complete = EXCLUDED.solar_energy_is_complete,
                    mean_relative_pressure_inhg = EXCLUDED.mean_relative_pressure_inhg,
                    lightning_strikes = EXCLUDED.lightning_strikes,
                    sample_count = EXCLUDED.sample_count,
                    calculated_at = NOW()
                """,
                (start, end, start, end, start, end, observation_date, observation_date),
            )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate and persist a daily weather fingerprint.")
    parser.add_argument(
        "date",
        nargs="?",
        default="yesterday",
        help="Station-local YYYY-MM-DD date, or 'yesterday' (default).",
    )
    args = parser.parse_args()

    observation_date = parse_date(args.date)
    calculate_and_upsert(observation_date)
    print(f"Calculated daily weather fingerprint for {observation_date}", flush=True)


if __name__ == "__main__":
    main()
