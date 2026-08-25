from dataclasses import dataclass
from datetime import datetime

@dataclass
class IrradianceReading:
    observed_at: datetime
    irradiance: float

    def __str__(self):
        return f"{self.observed_at}: {self.irradiance}"

    def __repr__(self):
        return f"IrradianceReading(observed_at={self.observed_at}, irradiance={self.irradiance})"