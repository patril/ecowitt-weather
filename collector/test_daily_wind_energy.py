import os
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql://unused")

from daily_wind_energy import (
    DailyWindEnergy,
    DRY_AIR_GAS_CONSTANT,
    INHG_TO_PA,
    MPH_TO_MPS,
)
from dto.WindSpeedReading import WindSpeedReading


def reading(
    hour: int,
    minute: int,
    wind_speed_mph: float,
    temp_f: float = 59.0,
    humidity_pct: float = 0.0,
    pressure_inhg: float = 29.92,
) -> WindSpeedReading:
    return WindSpeedReading(
        observed_at=datetime(2026, 8, 25, hour, minute, tzinfo=timezone.utc),
        wind_speed_mph=wind_speed_mph,
        outdoor_temp_f=temp_f,
        outdoor_humidity_pct=humidity_pct,
        absolute_pressure_inhg=pressure_inhg,
    )


def calculate(readings, max_gap_seconds=3600):
    start = readings[0].observed_at if readings else datetime(2026, 8, 25, tzinfo=timezone.utc)
    end = readings[-1].observed_at if readings else start + timedelta(days=1)
    with patch("daily_wind_energy.get_wind_speed_readings", return_value=readings), patch(
        "daily_wind_energy.station_day_bounds", return_value=(start, end)
    ):
        return DailyWindEnergy(
            date(2026, 8, 25),
            max_gap_seconds=max_gap_seconds,
        ).calculate()


class DailyWindEnergyTests(unittest.TestCase):
    def test_dry_air_density_uses_absolute_pressure_and_temperature(self):
        sample = reading(12, 0, 10, temp_f=59.0, humidity_pct=0.0, pressure_inhg=29.92)
        density = DailyWindEnergy._air_density_kg_m3(sample)
        expected = (29.92 * INHG_TO_PA) / (DRY_AIR_GAS_CONSTANT * 288.15)

        self.assertAlmostEqual(density, expected, places=6)

    def test_lower_station_pressure_reduces_air_density(self):
        sea_level = DailyWindEnergy._air_density_kg_m3(reading(12, 0, 10, pressure_inhg=29.92))
        mountain = DailyWindEnergy._air_density_kg_m3(reading(12, 0, 10, pressure_inhg=24.90))

        self.assertLess(mountain, sea_level)

    def test_humidity_reduces_air_density_at_same_temperature_and_pressure(self):
        dry = DailyWindEnergy._air_density_kg_m3(reading(12, 0, 10, humidity_pct=0.0))
        humid = DailyWindEnergy._air_density_kg_m3(reading(12, 0, 10, humidity_pct=90.0))

        self.assertLess(humid, dry)

    def test_constant_wind_integrates_power_density_over_time(self):
        samples = [reading(12, 0, 10), reading(13, 0, 10)]
        result = calculate(samples)
        density = DailyWindEnergy._air_density_kg_m3(samples[0])
        expected = 0.5 * density * (10 * MPH_TO_MPS) ** 3

        self.assertAlmostEqual(result.energy_wh_m2, expected)
        self.assertAlmostEqual(result.mean_air_density_kg_m3, density)
        self.assertTrue(result.is_complete)

    def test_trapezoid_uses_each_endpoints_power_density(self):
        first = reading(12, 0, 0, pressure_inhg=29.92)
        second = reading(13, 0, 10, pressure_inhg=24.90)
        result = calculate([first, second])
        endpoint_power = 0.5 * DailyWindEnergy._air_density_kg_m3(second) * (10 * MPH_TO_MPS) ** 3

        self.assertAlmostEqual(result.energy_wh_m2, endpoint_power / 2.0)

    def test_large_gap_is_not_interpolated(self):
        result = calculate([
            reading(12, 0, 10),
            reading(12, 1, 10),
            reading(13, 1, 10),
        ], max_gap_seconds=300)

        self.assertEqual(result.gap_count, 1)
        self.assertEqual(result.max_gap_seconds, 3600)
        self.assertFalse(result.is_complete)

    def test_empty_and_single_reading_days_are_incomplete(self):
        empty = calculate([])
        single = calculate([reading(12, 0, 10)])

        self.assertFalse(empty.is_complete)
        self.assertIsNone(empty.mean_air_density_kg_m3)
        self.assertFalse(single.is_complete)


if __name__ == "__main__":
    unittest.main()
