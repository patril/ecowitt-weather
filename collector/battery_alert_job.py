import os

import requests

from battery_alert import send_low_battery_alert

USE_MOCK_GW3000 = os.environ.get("USE_MOCK_GW3000", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ECOWITT_REAL_URL = os.environ.get(
    "ECOWITT_REAL_URL", "http://192.168.4.131/get_livedata_info"
)
MOCK_GW3000_URL = os.environ.get(
    "MOCK_GW3000_URL", "http://mock-gw3000:8080/get_livedata_info"
)
ECOWITT_URL = MOCK_GW3000_URL if USE_MOCK_GW3000 else ECOWITT_REAL_URL
PUSHOVER_USER_KEY = os.environ.get("PUSHOVER_USER_KEY", "")
PUSHOVER_API_TOKEN = os.environ.get("PUSHOVER_API_TOKEN", "")


def main():
    if not PUSHOVER_USER_KEY.strip() or not PUSHOVER_API_TOKEN.strip():
        print("Battery alert check skipped: Pushover credentials are not configured", flush=True)
        return

    response = requests.get(ECOWITT_URL, timeout=10)
    response.raise_for_status()
    payload = response.json()

    if send_low_battery_alert(payload, PUSHOVER_USER_KEY, PUSHOVER_API_TOKEN):
        print("Sent low weather sensor battery alert", flush=True)
    else:
        print("Battery check complete: no low sensor batteries", flush=True)


if __name__ == "__main__":
    main()
