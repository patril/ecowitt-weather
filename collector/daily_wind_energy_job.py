import argparse
from datetime import date, datetime, timedelta

from daily_wind_energy import DailyWindEnergy, STANDARD_AIR_DENSITY_KG_M3
from dao import STATION_TIMEZONE, upsert_daily_wind_energy


def parse_date(value: str) -> date:
    if value == "yesterday":
        return datetime.now(STATION_TIMEZONE).date() - timedelta(days=1)
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate and persist daily wind energy density.")
    parser.add_argument("date", nargs="?", default="yesterday")
    parser.add_argument("--max-gap-seconds", type=int, default=300)
    parser.add_argument("--air-density-kg-m3", type=float, default=STANDARD_AIR_DENSITY_KG_M3)
    args = parser.parse_args()

    observation_date = parse_date(args.date)
    result = DailyWindEnergy(
        observation_date,
        max_gap_seconds=args.max_gap_seconds,
        air_density_kg_m3=args.air_density_kg_m3,
    ).calculate()
    upsert_daily_wind_energy(result)

    print(
        f"{result.observation_date}: {result.energy_kwh_m2:.4f} kWh/m² "
        f"samples={result.sample_count} gaps={result.gap_count} "
        f"max_gap={result.max_gap_seconds:.1f}s complete={result.is_complete} "
        f"rho={result.air_density_kg_m3:.3f} kg/m³",
        flush=True,
    )


if __name__ == "__main__":
    main()
