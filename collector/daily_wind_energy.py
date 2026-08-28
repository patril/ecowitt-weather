from dataclasses import dataclass
from datetime import date, timezone
import math

from dao import get_wind_speed_readings, station_day_bounds
from dto.WindSpeedReading import WindSpeedReading

MPH_TO_MPS = 0.44704
INHG_TO_PA = 3386.389
DRY_AIR_GAS_CONSTANT = 287.05
WATER_VAPOR_GAS_CONSTANT = 461.5


@dataclass(frozen=True)
class DailyWindEnergyResult:
    observation_date: date
    energy_wh_m2: float
    sample_count: int
    gap_count: int
    max_gap_seconds: float
    is_complete: bool
    mean_air_density_kg_m3: float | None

    @property
    def energy_kwh_m2(self) -> float:
        return self.energy_wh_m2 / 1000.0


class DailyWindEnergy:
    def __init__(self, date: date, max_gap_seconds: int = 300):
        self.date = date
        self.max_gap_seconds = max_gap_seconds

    def calculate(self) -> DailyWindEnergyResult:
        readings = get_wind_speed_readings(self.date)
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
            max_gap_seconds = (
                day_end.astimezone(timezone.utc) - day_start.astimezone(timezone.utc)
            ).total_seconds()

        densities = [self._air_density_kg_m3(reading) for reading in readings]
        mean_air_density = sum(densities) / len(densities) if densities else None

        return DailyWindEnergyResult(
            observation_date=self.date,
            energy_wh_m2=energy_wh_m2,
            sample_count=len(readings),
            gap_count=len(gaps),
            max_gap_seconds=max_gap_seconds,
            is_complete=len(readings) >= 2 and not gaps,
            mean_air_density_kg_m3=mean_air_density,
        )

    @staticmethod
    def _air_density_kg_m3(reading: WindSpeedReading) -> float:
        temperature_c = (reading.outdoor_temp_f - 32.0) * 5.0 / 9.0
        temperature_k = temperature_c + 273.15
        pressure_pa = reading.absolute_pressure_inhg * INHG_TO_PA

        saturation_vapor_pressure_pa = 610.94 * math.exp(
            17.625 * temperature_c / (temperature_c + 243.04)
        )
        vapor_pressure_pa = (
            reading.outdoor_humidity_pct / 100.0
        ) * saturation_vapor_pressure_pa
        dry_air_pressure_pa = pressure_pa - vapor_pressure_pa

        return (
            dry_air_pressure_pa / (DRY_AIR_GAS_CONSTANT * temperature_k)
            + vapor_pressure_pa / (WATER_VAPOR_GAS_CONSTANT * temperature_k)
        )

    def _power_density_w_m2(self, reading: WindSpeedReading) -> float:
        wind_speed_m_s = reading.wind_speed_mph * MPH_TO_MPS
        air_density_kg_m3 = self._air_density_kg_m3(reading)
        return 0.5 * air_density_kg_m3 * wind_speed_m_s ** 3

    def _trapezoidal_integration(
        self,
        readings: tuple[WindSpeedReading, WindSpeedReading],
    ) -> float:
        hours_elapsed = (
            readings[1].observed_at - readings[0].observed_at
        ).total_seconds() / 3600.0
        average_power_density = (
            self._power_density_w_m2(readings[0])
            + self._power_density_w_m2(readings[1])
        ) / 2.0
        return hours_elapsed * average_power_density
