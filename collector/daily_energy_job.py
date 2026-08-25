import argparse
from datetime import date, datetime, timedelta

from daily_energy import DailyEnergy
from dao import STATION_TIMEZONE, upsert_daily_solar_energy


def parse_date(value: str) -> date:
    if value == "yesterday":
        return datetime.now(STATION_TIMEZONE).date() - timedelta(days=1)
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate and persist daily solar energy.")
    parser.add_argument(
        "date",
        nargs="?",
        default="yesterday",
        help="Station-local YYYY-MM-DD date, or 'yesterday' (default).",
    )
    parser.add_argument(
        "--max-gap-seconds",
        type=int,
        default=300,
        help="Do not interpolate across a sampling gap larger than this (default: 300).",
    )
    args = parser.parse_args()

    observation_date = parse_date(args.date)
    result = DailyEnergy(observation_date, args.max_gap_seconds).calculate()
    upsert_daily_solar_energy(result)

    print(
        f"{result.observation_date}: {result.energy_kwh_m2:.4f} kWh/m² "
        f"samples={result.sample_count} gaps={result.gap_count} "
        f"max_gap={result.max_gap_seconds:.1f}s complete={result.is_complete}",
        flush=True,
    )


if __name__ == "__main__":
    main()
