import unittest
from datetime import datetime

from lightning_alert import LightningAlerter


class FakeResponse:
    def raise_for_status(self):
        pass


class LightningAlerterTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.now = 0.0

        def post(url, data, timeout):
            self.calls.append((url, data, timeout))
            return FakeResponse()

        self.alerter = LightningAlerter(
            user_key="user-key",
            api_token="api-token",
            post=post,
            clock=lambda: self.now,
        )

    def lightning(self, distance, count=1, minute=0):
        return {
            "last_strike_at_local": datetime(2026, 8, 31, 13, minute),
            "distance_miles": distance,
            "cumulative_count": count,
        }

    def test_sends_normal_priority_notification_with_default_sound(self):
        sent = self.alerter.maybe_notify(self.lightning(7.5))

        self.assertTrue(sent)
        self.assertEqual(len(self.calls), 1)
        _, data, timeout = self.calls[0]
        self.assertEqual(timeout, 10)
        self.assertEqual(data["token"], "api-token")
        self.assertEqual(data["user"], "user-key")
        self.assertEqual(data["title"], "Nearby Lightning")
        self.assertEqual(data["message"], "Lightning struck within 7.5 miles.")
        self.assertEqual(data["priority"], 0)
        self.assertNotIn("sound", data)

    def test_default_radius_is_ten_miles(self):
        self.assertFalse(self.alerter.maybe_notify(self.lightning(10.1)))
        self.assertEqual(self.calls, [])

    def test_configurable_radius_is_respected(self):
        alerter = LightningAlerter(
            user_key="user-key",
            api_token="api-token",
            radius_miles=5,
            post=lambda *args, **kwargs: FakeResponse(),
            clock=lambda: self.now,
        )

        self.assertFalse(alerter.maybe_notify(self.lightning(5.1)))

    def test_distinct_strikes_are_rate_limited_to_five_minutes(self):
        self.assertTrue(self.alerter.maybe_notify(self.lightning(4, count=1, minute=0)))

        self.now = 299
        self.assertFalse(self.alerter.maybe_notify(self.lightning(3, count=2, minute=1)))

        self.now = 300
        self.assertTrue(self.alerter.maybe_notify(self.lightning(2, count=3, minute=5)))
        self.assertEqual(len(self.calls), 2)

    def test_same_strike_is_not_repeated_after_cooldown(self):
        strike = self.lightning(4, count=1, minute=0)
        self.assertTrue(self.alerter.maybe_notify(strike))

        self.now = 600
        self.assertFalse(self.alerter.maybe_notify(strike))
        self.assertEqual(len(self.calls), 1)

    def test_missing_credentials_disable_notifications(self):
        alerter = LightningAlerter(
            user_key="",
            api_token="",
            post=lambda *args, **kwargs: self.fail("POST should not be called"),
        )

        self.assertFalse(alerter.maybe_notify(self.lightning(4)))


if __name__ == "__main__":
    unittest.main()
