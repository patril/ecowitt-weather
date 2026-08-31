import unittest

from battery_alert import LOW_BATTERY_LEVEL, low_battery_sensors, send_low_battery_alert


class FakeResponse:
    def raise_for_status(self):
        pass


class BatteryAlertTests(unittest.TestCase):
    def payload(self, wh40="5", ws90="5", wh57="5"):
        return {
            "rain": [{"id": "0x13", "battery": wh40}],
            "piezoRain": [{"id": "0x13", "battery": ws90, "ws90cap_volt": "5.3"}],
            "lightning": [{"battery": wh57}],
        }

    def test_threshold_is_level_one_or_lower(self):
        self.assertEqual(LOW_BATTERY_LEVEL, 1.0)
        low = low_battery_sensors(self.payload(wh40="1", ws90="1.1", wh57="0"))
        self.assertEqual(
            low,
            [("WH40 rain gauge", 1.0), ("WH57 lightning detector", 0.0)],
        )

    def test_ignores_ws90_capacitor_voltage(self):
        payload = self.payload(ws90="5")
        payload["piezoRain"][0]["ws90cap_volt"] = "0.2"
        self.assertEqual(low_battery_sensors(payload), [])

    def test_sends_one_summary_notification_for_all_low_sensors(self):
        calls = []

        def post(url, data, timeout):
            calls.append((url, data, timeout))
            return FakeResponse()

        sent = send_low_battery_alert(
            self.payload(wh40="1", ws90="5", wh57="0"),
            "user-key",
            "api-token",
            post=post,
        )

        self.assertTrue(sent)
        self.assertEqual(len(calls), 1)
        _, data, timeout = calls[0]
        self.assertEqual(timeout, 10)
        self.assertEqual(data["title"], "Low Weather Sensor Battery")
        self.assertEqual(
            data["message"],
            "Replace batteries: WH40 rain gauge (1/5), WH57 lightning detector (0/5).",
        )
        self.assertEqual(data["priority"], 0)
        self.assertNotIn("sound", data)

    def test_no_notification_when_batteries_are_healthy(self):
        self.assertFalse(
            send_low_battery_alert(
                self.payload(),
                "user-key",
                "api-token",
                post=lambda *args, **kwargs: self.fail("POST should not be called"),
            )
        )

    def test_missing_credentials_disable_notification(self):
        self.assertFalse(
            send_low_battery_alert(
                self.payload(wh40="0"),
                "",
                "",
                post=lambda *args, **kwargs: self.fail("POST should not be called"),
            )
        )


if __name__ == "__main__":
    unittest.main()
