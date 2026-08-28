import argparse
from datetime import date, datetime, timedelta

from daily_wind_energy import DailyWindEnergy
from dao import STATION_TIMEZONE, upsert_daily_wind_energy


def parse_date(value: str) -> date:
    if value == "yesterday":
        return datetime.now(STATION_TIMEZONE).date() - timedelta(days=1)
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate and persist daily wind energy density.")
    parser.add_argument("date", nargs="?", default="yesterday")
    parser.add_argument("--max-gap-seconds", type=int, default=300)
    args = parser.parse_args()

    observation_date = parse_date(args.date)
    result = DailyWindEnergy(
        observation_date,
        max_gap_seconds=args.max_gap_seconds,
    ).calculate()
    upsert_daily_wind_energy(result)

    density_text = (
        f"{result.mean_air_density_kg_m3:.3f} kg/m³"
        if result.mean_air_density_kg_m3 is not None
        else "n/a"
    )
    print(
        f"{result.observation_date}: {result.energy_kwh_m2:.4f} kWh/m² "
        f"samples={result.sample_count} gaps={result.gap_count} "
        f"max_gap={result.max_gap_seconds:.1f}s complete={result.is_complete} "
        f"mean_rho={density_text}",
        flush=True,
    )


if __name__ == "__main__":
    main()
