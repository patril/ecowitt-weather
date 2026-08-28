CREATE TABLE IF NOT EXISTS daily_wind_energy (
    observation_date   DATE PRIMARY KEY,
    energy_wh_m2       DOUBLE PRECISION NOT NULL,
    air_density_kg_m3  DOUBLE PRECISION NOT NULL,
    sample_count       INTEGER NOT NULL,
    gap_count          INTEGER NOT NULL DEFAULT 0,
    max_gap_seconds    DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_complete        BOOLEAN NOT NULL,
    calculated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
