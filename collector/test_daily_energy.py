import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql://unused")

from daily_energy import DailyEnergy
from dao import station_day_bounds
from dto.IrradianceReading import IrradianceReading


def reading(hour: int, minute: int, irradiance: float) -> IrradianceReading:
    return IrradianceReading(
        observed_at=datetime(2026, 8, 25, hour, minute, tzinfo=timezone.utc),
        irradiance=irradiance,
    )


class DailyEnergyTests(unittest.TestCase):
    @patch("daily_energy.get_irradiance_readings")
    def test_trapezoidal_integration_returns_wh_per_square_meter(self, get_readings):
        get_readings.return_value = [reading(12, 0, 0), reading(13, 0, 1000)]

        result = DailyEnergy(date(2026, 8, 25), max_gap_seconds=3600).calculate()

        self.assertAlmostEqual(result.energy_wh_m2, 500.0)
        self.assertAlmostEqual(result.energy_kwh_m2, 0.5)
        self.assertTrue(result.is_complete)

    @patch("daily_energy.get_irradiance_readings")
    def test_irregular_sampling_intervals_are_respected(self, get_readings):
        get_readings.return_value = [
            reading(12, 0, 100),
            reading(12, 10, 200),
            reading(12, 40, 400),
        ]

        result = DailyEnergy(date(2026, 8, 25), max_gap_seconds=3600).calculate()

        self.assertAlmostEqual(result.energy_wh_m2, 175.0)
        self.assertEqual(result.sample_count, 3)

    @patch("daily_energy.get_irradiance_readings")
    def test_large_gap_is_not_interpolated_and_marks_result_incomplete(self, get_readings):
        get_readings.return_value = [
            reading(12, 0, 100),
            reading(12, 1, 100),
            reading(13, 1, 100),
        ]

        result = DailyEnergy(date(2026, 8, 25), max_gap_seconds=300).calculate()

        self.assertAlmostEqual(result.energy_wh_m2, 100 / 60)
        self.assertEqual(result.gap_count, 1)
        self.assertEqual(result.max_gap_seconds, 3600)
        self.assertFalse(result.is_complete)

    @patch("daily_energy.get_irradiance_readings")
    def test_empty_and_single_reading_days_are_incomplete(self, get_readings):
        for readings in ([], [reading(12, 0, 500)]):
            with self.subTest(sample_count=len(readings)):
                get_readings.return_value = readings
                result = DailyEnergy(date(2026, 8, 25)).calculate()
                self.assertEqual(result.energy_wh_m2, 0)
                self.assertFalse(result.is_complete)

    def test_station_day_bounds_follow_dst(self):
        spring_start, spring_end = station_day_bounds(date(2026, 3, 8))
        fall_start, fall_end = station_day_bounds(date(2026, 11, 1))

        spring_hours = (spring_end.astimezone(timezone.utc) - spring_start.astimezone(timezone.utc)).total_seconds() / 3600
        fall_hours = (fall_end.astimezone(timezone.utc) - fall_start.astimezone(timezone.utc)).total_seconds() / 3600

        self.assertEqual(spring_hours, 23)
        self.assertEqual(fall_hours, 25)


if __name__ == "__main__":
    unittest.main()
