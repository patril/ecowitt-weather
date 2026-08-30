import unittest
from datetime import datetime, timedelta, timezone

from dto.IrradianceReading import IrradianceReading
from sky_condition import clear_sky_ghi, estimate_sky_condition


class SkyConditionTests(unittest.TestCase):
    latitude = 0.0
    longitude = 0.0
    midday = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)

    def readings_for_indices(self, indices):
        readings = []
        start = self.midday - timedelta(minutes=len(indices) - 1)
        for offset, index in enumerate(indices):
            observed_at = start + timedelta(minutes=offset)
            expected = clear_sky_ghi(observed_at, self.latitude, self.longitude)
            readings.append(IrradianceReading(observed_at, expected * index))
        return readings

    def test_clear_sky_ghi_is_high_near_equinox_noon_at_equator(self):
        self.assertGreater(clear_sky_ghi(self.midday, self.latitude, self.longitude), 900.0)

    def test_stable_high_irradiance_is_clear(self):
        expected = clear_sky_ghi(self.midday, self.latitude, self.longitude)
        result = estimate_sky_condition(
            self.midday,
            expected * 0.95,
            self.readings_for_indices([0.94, 0.96, 0.95, 0.94, 0.95]),
            self.latitude,
            self.longitude,
        )
        self.assertEqual(result.condition, "Clear")

    def test_rapidly_changing_irradiance_is_variable_clouds(self):
        expected = clear_sky_ghi(self.midday, self.latitude, self.longitude)
        result = estimate_sky_condition(
            self.midday,
            expected * 0.55,
            self.readings_for_indices([0.95, 0.42, 1.08, 0.51, 0.55]),
            self.latitude,
            self.longitude,
        )
        self.assertEqual(result.condition, "Variable clouds")

    def test_low_stable_irradiance_is_heavy_cloud(self):
        expected = clear_sky_ghi(self.midday, self.latitude, self.longitude)
        result = estimate_sky_condition(
            self.midday,
            expected * 0.20,
            self.readings_for_indices([0.20, 0.21, 0.19, 0.20, 0.20]),
            self.latitude,
            self.longitude,
        )
        self.assertEqual(result.condition, "Heavy cloud")

    def test_night_does_not_guess_cloud_cover(self):
        midnight = datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)
        result = estimate_sky_condition(midnight, 0.0, [], self.latitude, self.longitude)
        self.assertEqual(result.condition, "Night / low sun")

    def test_missing_coordinates_is_unavailable(self):
        result = estimate_sky_condition(self.midday, 500.0, [], None, None)
        self.assertEqual(result.condition, "Unavailable")


if __name__ == "__main__":
    unittest.main()
