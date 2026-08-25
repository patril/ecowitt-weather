from datetime import date
from collector.dao import get_irradiance_readings
from collector.dto.IrradianceReading import IrradianceReading

class DailyEnergy:
    def __init__(self, date: date):
        self.date = date

    def __str__(self):
        return f"{self.date}"

    def __repr__(self):
        return f"DailyEnergy(date={self.date})"

    def get_energy(self):
        readings = get_irradiance_readings(self.date)

        energy = 0

        for i, reading in enumerate(readings):
            if (i > 0):
                tuple = (readings[i-1], reading)
                energy += self._trapezoidal_integration(tuple)

        return energy

    def _trapezoidal_integration(self, readings: tuple[IrradianceReading, IrradianceReading]):
        seconds_elapsed = (readings[1].observed_at - readings[0].observed_at).total_seconds()
        return seconds_elapsed * ((readings[0].irradiance + readings[1].irradiance) / 2)