import requests

PUSHOVER_MESSAGES_URL = "https://api.pushover.net/1/messages.json"
LOW_BATTERY_LEVEL = 1.0

SENSOR_SECTIONS = {
    "rain": "WH40 rain gauge",
    "piezoRain": "WS90 sensor array",
    "lightning": "WH57 lightning detector",
}


def _battery_level(entries):
    for entry in entries or []:
        value = entry.get("battery")
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def low_battery_sensors(payload):
    low = []
    for section, sensor_name in SENSOR_SECTIONS.items():
        level = _battery_level(payload.get(section))
        if level is not None and level <= LOW_BATTERY_LEVEL:
            low.append((sensor_name, level))
    return low


def format_level(level):
    return f"{level:g}/5"


def send_low_battery_alert(payload, user_key, api_token, post=None):
    user_key = (user_key or "").strip()
    api_token = (api_token or "").strip()
    if not user_key or not api_token:
        return False

    low = low_battery_sensors(payload)
    if not low:
        return False

    message = "Replace batteries: " + ", ".join(
        f"{sensor_name} ({format_level(level)})" for sensor_name, level in low
    ) + "."

    response = (post or requests.post)(
        PUSHOVER_MESSAGES_URL,
        data={
            "token": api_token,
            "user": user_key,
            "title": "Low Weather Sensor Battery",
            "message": message,
            "priority": 0,
        },
        timeout=10,
    )
    response.raise_for_status()
    return True
