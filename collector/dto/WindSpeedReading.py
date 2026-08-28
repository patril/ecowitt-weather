from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WindSpeedReading:
    observed_at: datetime
    wind_speed_mph: float
