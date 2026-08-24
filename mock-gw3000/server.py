import json
import math
import random
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 8080
START = time.time()


def f(value, digits=1):
    return f"{value:.{digits}f}"


def payload():
    elapsed = time.time() - START
    phase = elapsed / 180.0

    temp = 80.0 + 2.5 * math.sin(phase) + random.uniform(-0.15, 0.15)
    humidity = 78 + 5 * math.sin(phase + 1.7)
    dewpoint = temp - 6.0
    wind = max(0.0, 4.5 + 2.0 * math.sin(phase * 2.3) + random.uniform(-0.5, 0.5))
    gust = wind + random.uniform(0.0, 3.0)
    solar = max(0.0, 420 + 180 * math.sin(phase * 0.7))
    wind_dir = int((160 + elapsed / 8) % 360)
    lightning_count = 12 + int(elapsed // 600)
    last_strike = datetime.now().replace(microsecond=0).isoformat()

    return {
        "common_list": [
            {"id": "0x02", "val": f(temp), "unit": "F"},
            {"id": "0x07", "val": f"{int(humidity)}%"},
            {"id": "3", "val": f(temp + 0.3), "unit": "F"},
            {"id": "5", "val": "0.666 kPa"},
            {"id": "0x03", "val": f(dewpoint), "unit": "F"},
            {"id": "0x0B", "val": f(wind, 2) + " mph"},
            {"id": "0x0C", "val": f(gust, 2) + " mph"},
            {"id": "0x19", "val": f(max(gust, 10.07), 2) + " mph"},
            {"id": "0x15", "val": f(solar, 2) + " W/m2"},
            {"id": "0x17", "val": str(max(0, min(11, int(solar / 120))))},
            {"id": "0x0A", "val": str(wind_dir)},
            {"id": "0x6D", "val": "135"},
        ],
        "rain": [
            {"id": "0x0D", "val": "0.17 in"},
            {"id": "0x0E", "val": "0.00 in/Hr"},
            {"id": "0x7D", "val": "0.06 in"},
            {"id": "0x7C", "val": "0.17 in"},
            {"id": "0x10", "val": "0.17 in"},
            {"id": "0x11", "val": "1.38 in"},
            {"id": "0x12", "val": "2.49 in"},
            {"id": "0x13", "val": "2.49 in", "battery": "5", "voltage": "1.7"},
        ],
        "piezoRain": [
            {"id": "srain_piezo", "val": "1"},
            {"id": "0x0D", "val": "1.07 in"},
            {"id": "0x0E", "val": "0.00 in/Hr"},
            {"id": "0x7D", "val": "0.04 in"},
            {"id": "0x7C", "val": "0.19 in"},
            {"id": "0x10", "val": "0.18 in"},
            {"id": "0x11", "val": "1.07 in"},
            {"id": "0x12", "val": "1.25 in"},
            {"id": "0x13", "val": "1.25 in", "battery": "5", "voltage": "3.28", "ws90cap_volt": "5.3", "ws90_ver": "162"},
        ],
        "wh25": [{"intemp": "75.6", "unit": "F", "inhumi": "50%", "abs": "29.95 inHg", "rel": "29.95 inHg"}],
        "lightning": [{"distance": "16.7 mi", "date": last_strike, "timestamp": datetime.now().strftime("%m/%d/%Y %H:%M:%S"), "count": str(lightning_count), "battery": "5"}],
        "debug": [{"heap": "74900", "runtime": str(int(elapsed)), "usr_interval": "--", "is_cnip": False}],
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/get_livedata_info"):
            self.send_error(404)
            return
        body = json.dumps(payload()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("mock-gw3000:", fmt % args, flush=True)


if __name__ == "__main__":
    print(f"Mock GW3000 listening on http://{HOST}:{PORT}/get_livedata_info", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
