import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://unused")

from collector import apply_piezo_rain_rate_fallback


class PiezoRainRateFallbackTests(unittest.TestCase):
    def test_wh40_rate_is_preferred_when_both_detect_rain(self):
        wh40 = {"rain_rate_in_hr": 0.12, "daily_rain_in": 1.25, "source": "wh40"}
        ws90 = {"rain_rate_in_hr": 0.35, "daily_rain_in": 1.40, "source": "ws90"}

        effective, source = apply_piezo_rain_rate_fallback(wh40, ws90)

        self.assertEqual(0.12, effective["rain_rate_in_hr"])
        self.assertEqual(1.25, effective["daily_rain_in"])
        self.assertEqual("wh40", source)

    def test_ws90_rate_is_used_when_wh40_is_not_yet_detecting_rain(self):
        wh40 = {"rain_rate_in_hr": 0.0, "daily_rain_in": 1.25, "source": "wh40"}
        ws90 = {"rain_rate_in_hr": 0.08, "daily_rain_in": 1.40, "source": "ws90"}

        effective, source = apply_piezo_rain_rate_fallback(wh40, ws90)

        self.assertEqual(0.08, effective["rain_rate_in_hr"])
        self.assertEqual(1.25, effective["daily_rain_in"])
        self.assertEqual("wh40", effective["source"])
        self.assertEqual("ws90", source)

    def test_wh40_totals_are_never_replaced_by_ws90_totals(self):
        wh40 = {
            "rain_rate_in_hr": None,
            "event_rain_in": 0.10,
            "daily_rain_in": 1.25,
            "weekly_rain_in": 2.50,
            "monthly_rain_in": 5.00,
            "yearly_rain_in": 30.00,
            "source": "wh40",
        }
        ws90 = {
            "rain_rate_in_hr": 0.15,
            "event_rain_in": 0.20,
            "daily_rain_in": 1.50,
            "weekly_rain_in": 2.75,
            "monthly_rain_in": 5.25,
            "yearly_rain_in": 30.25,
            "source": "ws90",
        }

        effective, source = apply_piezo_rain_rate_fallback(wh40, ws90)

        self.assertEqual(0.15, effective["rain_rate_in_hr"])
        self.assertEqual(0.10, effective["event_rain_in"])
        self.assertEqual(1.25, effective["daily_rain_in"])
        self.assertEqual(2.50, effective["weekly_rain_in"])
        self.assertEqual(5.00, effective["monthly_rain_in"])
        self.assertEqual(30.00, effective["yearly_rain_in"])
        self.assertEqual("ws90", source)

    def test_dry_readings_remain_wh40(self):
        wh40 = {"rain_rate_in_hr": 0.0, "source": "wh40"}
        ws90 = {"rain_rate_in_hr": 0.0, "source": "ws90"}

        effective, source = apply_piezo_rain_rate_fallback(wh40, ws90)

        self.assertEqual(0.0, effective["rain_rate_in_hr"])
        self.assertEqual("wh40", source)


if __name__ == "__main__":
    unittest.main()
