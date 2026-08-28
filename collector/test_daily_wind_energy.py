import os
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql://unused")

from daily_wind_energy import DailyWindEnergy, MPH_TO_MPS
from dto.WindSpeedReading import WindSpeedReading


def reading(hour: int, minute: int, wind_speed_mph: float) -> WindSpeedReading:
    return WindSpeedReading(
        observed_at=datetime(2026, 8, 25, hour, minute, tzinfo=timezone.utc),
        wind_speed_mph=wind_speed_mph,
    )


def calculate(readings, max_gap_seconds=3600, air_density_kg_m3=1.225):
    start = readings[0].observed_at if readings else datetime(2026, 8, 25, tzinfo=timezone.utc)
    end = readings[-1].observed_at if readings else start + timedelta(days=1)
    with patch("daily_wind_energy.get_wind_speed_readings", return_value=readings), patch(
        "daily_wind_energy.station_day_bounds", return_value=(start, end)
    ):
        return DailyWindEnergy(
            date(2026, 8, 25),
            max_gap_seconds=max_gap_seconds,
            air_density_kg_m3=air_density_kg_m3,
        ).calculate()


class DailyWindEnergyTests(unittest.TestCase):
    def test_constant_wind_integrates_power_density_over_time(self):
        speed_mph = 10.0
        result = calculate([reading(12, 0, speed_mph), reading(13, 0, speed_mph)])
        speed_m_s = speed_mph * MPH_TO_MPS
        expected = 0.5 * 1.225 * speed_m_s ** 3

        self.assertAlmostEqual(result.energy_wh_m2, expected)
        self.assertAlmostEqual(result.energy_kwh_m2, expected / 1000.0)
        self.assertTrue(result.is_complete)

    def test_trapezoid_is_applied_to_power_density_not_wind_speed(self):
        result = calculate([reading(12, 0, 0), reading(13, 0, 10)])
        endpoint_power = 0.5 * 1.225 * (10 * MPH_TO_MPS) ** 3

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
        self.assertFalse(calculate([]).is_complete)
        self.assertFalse(calculate([reading(12, 0, 10)]).is_complete)


if __name__ == "__main__":
    unittest.main()
