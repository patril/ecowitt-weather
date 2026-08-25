from dataclasses import dataclass
from datetime import date

from dao import get_irradiance_readings
from dto.IrradianceReading import IrradianceReading


@dataclass(frozen=True)
class DailyEnergyResult:
    observation_date: date
    energy_wh_m2: float
    sample_count: int
    gap_count: int
    max_gap_seconds: float
    is_complete: bool

    @property
    def energy_kwh_m2(self) -> float:
        return self.energy_wh_m2 / 1000.0


class DailyEnergy:
    def __init__(self, date: date, max_gap_seconds: int = 300):
        self.date = date
        self.max_gap_seconds = max_gap_seconds

    def __str__(self):
        return f"{self.date}"

    def __repr__(self):
        return f"DailyEnergy(date={self.date}, max_gap_seconds={self.max_gap_seconds})"

    def calculate(self) -> DailyEnergyResult:
        readings = get_irradiance_readings(self.date)
        energy_wh_m2 = 0.0
        gap_count = 0
        max_gap_seconds = 0.0

        for previous, current in zip(readings, readings[1:]):
            seconds_elapsed = (current.observed_at - previous.observed_at).total_seconds()
            max_gap_seconds = max(max_gap_seconds, seconds_elapsed)

            if seconds_elapsed <= 0:
                continue
            if seconds_elapsed > self.max_gap_seconds:
                gap_count += 1
                continue

            energy_wh_m2 += self._trapezoidal_integration((previous, current))

        return DailyEnergyResult(
            observation_date=self.date,
            energy_wh_m2=energy_wh_m2,
            sample_count=len(readings),
            gap_count=gap_count,
            max_gap_seconds=max_gap_seconds,
            is_complete=len(readings) >= 2 and gap_count == 0,
        )

    def get_energy(self) -> float:
        """Return integrated daily solar energy in Wh/m²."""
        return self.calculate().energy_wh_m2

    def _trapezoidal_integration(
        self,
        readings: tuple[IrradianceReading, IrradianceReading],
    ) -> float:
        hours_elapsed = (
            readings[1].observed_at - readings[0].observed_at
        ).total_seconds() / 3600.0
        average_irradiance = (readings[0].irradiance + readings[1].irradiance) / 2.0
        return hours_elapsed * average_irradiance
