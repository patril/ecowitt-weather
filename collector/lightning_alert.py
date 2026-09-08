import time

import requests

PUSHOVER_MESSAGES_URL = "https://api.pushover.net/1/messages.json"
DEFAULT_RADIUS_MILES = 10.0
NOTIFICATION_COOLDOWN_SECONDS = 300.0


class LightningAlerter:
    def __init__(
        self,
        user_key,
        api_token,
        radius_miles=DEFAULT_RADIUS_MILES,
        post=None,
        clock=None,
    ):
        self.user_key = (user_key or "").strip()
        self.api_token = (api_token or "").strip()
        self.radius_miles = radius_miles
        self._post = post or requests.post
        self._clock = clock or time.monotonic
        self._last_notification_at = None
        self._last_seen_strike = None

    @property
    def enabled(self):
        return bool(self.user_key and self.api_token)

    def maybe_notify(self, lightning):
        if not self.enabled or not lightning:
            return False

        distance = lightning.get("distance_miles")
        if distance is None:
            return False

        strike_identity = (
            lightning.get("last_strike_at_local"),
            lightning.get("cumulative_count"),
        )
        if strike_identity == self._last_seen_strike:
            return False

        if distance > self.radius_miles:
            self._last_seen_strike = strike_identity
            return False

        now = self._clock()
        if (
            self._last_notification_at is not None
            and now - self._last_notification_at < NOTIFICATION_COOLDOWN_SECONDS
        ):
            self._last_seen_strike = strike_identity
            return False

        response = self._post(
            PUSHOVER_MESSAGES_URL,
            data={
                "token": self.api_token,
                "user": self.user_key,
                "title": "Nearby Lightning",
                "message": f"Lightning struck within {distance:g} miles.",
                "priority": 0,
            },
            timeout=10,
        )
        response.raise_for_status()

        self._last_notification_at = now
        self._last_seen_strike = strike_identity
        return True
