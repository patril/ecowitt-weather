from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WindSpeedReading:
    observed_at: datetime
    wind_speed_mph: float
    outdoor_temp_f: float
    outdoor_humidity_pct: float
    absolute_pressure_inhg: float
