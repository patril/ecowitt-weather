from dataclasses import dataclass
from datetime import date

from dao import get_irradiance_readings, station_day_bounds
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
        day_start, day_end = station_day_bounds(self.date)
        energy_wh_m2 = 0.0
        gaps: list[float] = []

        if readings:
            leading_gap = (readings[0].observed_at - day_start).total_seconds()
            trailing_gap = (day_end - readings[-1].observed_at).total_seconds()
            if leading_gap > self.max_gap_seconds:
                gaps.append(leading_gap)
            if trailing_gap > self.max_gap_seconds:
                gaps.append(trailing_gap)

        for previous, current in zip(readings, readings[1:]):
            seconds_elapsed = (current.observed_at - previous.observed_at).total_seconds()
            if seconds_elapsed <= 0:
                continue
            if seconds_elapsed > self.max_gap_seconds:
                gaps.append(seconds_elapsed)
                continue

            energy_wh_m2 += self._trapezoidal_integration((previous, current))

        if readings:
            all_intervals = [
                (current.observed_at - previous.observed_at).total_seconds()
                for previous, current in zip(readings, readings[1:])
                if current.observed_at > previous.observed_at
            ]
            all_intervals.extend([
                max(0.0, (readings[0].observed_at - day_start).total_seconds()),
                max(0.0, (day_end - readings[-1].observed_at).total_seconds()),
            ])
            max_gap_seconds = max(all_intervals, default=0.0)
        else:
            max_gap_seconds = (day_end - day_start).total_seconds()

        return DailyEnergyResult(
            observation_date=self.date,
            energy_wh_m2=energy_wh_m2,
            sample_count=len(readings),
            gap_count=len(gaps),
            max_gap_seconds=max_gap_seconds,
            is_complete=len(readings) >= 2 and not gaps,
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
