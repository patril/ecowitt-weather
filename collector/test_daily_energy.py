import os
import unittest
from datetime import date, datetime, timedelta, timezone
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


def calculate(readings, max_gap_seconds=3600):
    start = readings[0].observed_at if readings else datetime(2026, 8, 25, tzinfo=timezone.utc)
    end = readings[-1].observed_at if readings else start + timedelta(days=1)
    with patch("daily_energy.get_irradiance_readings", return_value=readings), patch(
        "daily_energy.station_day_bounds", return_value=(start, end)
    ):
        return DailyEnergy(date(2026, 8, 25), max_gap_seconds=max_gap_seconds).calculate()


class DailyEnergyTests(unittest.TestCase):
    def test_trapezoidal_integration_returns_wh_per_square_meter(self):
        result = calculate([reading(12, 0, 0), reading(13, 0, 1000)])

        self.assertAlmostEqual(result.energy_wh_m2, 500.0)
        self.assertAlmostEqual(result.energy_kwh_m2, 0.5)
        self.assertTrue(result.is_complete)

    def test_irregular_sampling_intervals_are_respected(self):
        result = calculate([
            reading(12, 0, 100),
            reading(12, 10, 200),
            reading(12, 40, 400),
        ])

        self.assertAlmostEqual(result.energy_wh_m2, 175.0)
        self.assertEqual(result.sample_count, 3)

    def test_large_internal_gap_is_not_interpolated(self):
        result = calculate([
            reading(12, 0, 100),
            reading(12, 1, 100),
            reading(13, 1, 100),
        ], max_gap_seconds=300)

        self.assertAlmostEqual(result.energy_wh_m2, 100 / 60)
        self.assertEqual(result.gap_count, 1)
        self.assertEqual(result.max_gap_seconds, 3600)
        self.assertFalse(result.is_complete)

    def test_missing_start_of_day_marks_result_incomplete(self):
        readings = [reading(12, 0, 100), reading(12, 1, 100)]
        day_start = readings[0].observed_at - timedelta(hours=2)
        day_end = readings[-1].observed_at

        with patch("daily_energy.get_irradiance_readings", return_value=readings), patch(
            "daily_energy.station_day_bounds", return_value=(day_start, day_end)
        ):
            result = DailyEnergy(date(2026, 8, 25), max_gap_seconds=300).calculate()

        self.assertEqual(result.gap_count, 1)
        self.assertFalse(result.is_complete)

    def test_empty_and_single_reading_days_are_incomplete(self):
        empty = calculate([])
        single = calculate([reading(12, 0, 500)])

        self.assertEqual(empty.energy_wh_m2, 0)
        self.assertFalse(empty.is_complete)
        self.assertEqual(single.energy_wh_m2, 0)
        self.assertFalse(single.is_complete)

    def test_station_day_bounds_follow_dst(self):
        spring_start, spring_end = station_day_bounds(date(2026, 3, 8))
        fall_start, fall_end = station_day_bounds(date(2026, 11, 1))

        spring_hours = (spring_end.astimezone(timezone.utc) - spring_start.astimezone(timezone.utc)).total_seconds() / 3600
        fall_hours = (fall_end.astimezone(timezone.utc) - fall_start.astimezone(timezone.utc)).total_seconds() / 3600

        self.assertEqual(spring_hours, 23)
        self.assertEqual(fall_hours, 25)


if __name__ == "__main__":
    unittest.main()
