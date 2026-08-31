from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import cos, exp, pi, radians, sin
from statistics import pstdev
from typing import Iterable

from dto.IrradianceReading import IrradianceReading

MIN_CLEAR_SKY_GHI_W_M2 = 75.0
VARIABLE_CLOUDS_STDDEV = 0.12
CLEAR_SKY_INDEX_THRESHOLD = 0.80
HEAVY_CLOUD_INDEX_THRESHOLD = 0.45


@dataclass(frozen=True)
class SkyConditionResult:
    observed_at: datetime
    condition: str
    clear_sky_index: float | None
    variability: float | None
    clear_sky_w_m2: float | None


def clear_sky_ghi(observed_at: datetime, latitude: float, longitude: float) -> float:
    """Estimate clear-sky global horizontal irradiance using the Haurwitz model.

    Solar position is calculated from UTC time and station coordinates. The
    Haurwitz model then converts solar zenith to clear-sky GHI. This keeps the
    estimator portable and dependency-free while avoiding climate-specific
    assumptions.
    """
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be between -90 and 90 degrees")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be between -180 and 180 degrees")
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")

    utc = observed_at.astimezone(timezone.utc)
    day_of_year = utc.timetuple().tm_yday
    fractional_hour = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
    gamma = 2.0 * pi / 365.0 * (day_of_year - 1 + (fractional_hour - 12.0) / 24.0)

    equation_of_time_minutes = 229.18 * (
        0.000075
        + 0.001868 * cos(gamma)
        - 0.032077 * sin(gamma)
        - 0.014615 * cos(2.0 * gamma)
        - 0.040849 * sin(2.0 * gamma)
    )
    solar_declination = (
        0.006918
        - 0.399912 * cos(gamma)
        + 0.070257 * sin(gamma)
        - 0.006758 * cos(2.0 * gamma)
        + 0.000907 * sin(2.0 * gamma)
        - 0.002697 * cos(3.0 * gamma)
        + 0.001480 * sin(3.0 * gamma)
    )

    utc_minutes = utc.hour * 60.0 + utc.minute + utc.second / 60.0
    true_solar_time_minutes = (utc_minutes + equation_of_time_minutes + 4.0 * longitude) % 1440.0
    hour_angle_degrees = true_solar_time_minutes / 4.0 - 180.0
    latitude_radians = radians(latitude)
    hour_angle_radians = radians(hour_angle_degrees)

    cos_zenith = (
        sin(latitude_radians) * sin(solar_declination)
        + cos(latitude_radians) * cos(solar_declination) * cos(hour_angle_radians)
    )
    if cos_zenith <= 0.0:
        return 0.0

    return 1098.0 * cos_zenith * exp(-0.059 / cos_zenith)


def _clear_sky_indices(
    readings: Iterable[IrradianceReading], latitude: float, longitude: float
) -> list[float]:
    indices = []
    for reading in readings:
        expected = clear_sky_ghi(reading.observed_at, latitude, longitude)
        if expected >= MIN_CLEAR_SKY_GHI_W_M2:
            indices.append(max(0.0, min(2.0, reading.irradiance / expected)))
    return indices


def estimate_sky_condition(
    observed_at: datetime,
    irradiance: float | None,
    recent_readings: Iterable[IrradianceReading],
    latitude: float | None,
    longitude: float | None,
) -> SkyConditionResult:
    if latitude is None or longitude is None or irradiance is None:
        return SkyConditionResult(observed_at, "Unavailable", None, None, None)

    expected = clear_sky_ghi(observed_at, latitude, longitude)
    if expected < MIN_CLEAR_SKY_GHI_W_M2:
        return SkyConditionResult(observed_at, "Night / low sun", None, None, expected)

    clear_sky_index = max(0.0, min(2.0, irradiance / expected))
    indices = _clear_sky_indices(recent_readings, latitude, longitude)
    variability = pstdev(indices) if len(indices) >= 3 else None

    if variability is not None and variability >= VARIABLE_CLOUDS_STDDEV:
        condition = "Variable clouds"
    elif clear_sky_index >= CLEAR_SKY_INDEX_THRESHOLD:
        condition = "Clear"
    elif clear_sky_index >= HEAVY_CLOUD_INDEX_THRESHOLD:
        condition = "Cloud-obscured"
    else:
        condition = "Heavy cloud"

    return SkyConditionResult(
        observed_at=observed_at,
        condition=condition,
        clear_sky_index=clear_sky_index,
        variability=variability,
        clear_sky_w_m2=expected,
    )
