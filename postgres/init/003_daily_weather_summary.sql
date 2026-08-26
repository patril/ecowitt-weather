CREATE TABLE IF NOT EXISTS daily_weather_summary (
    observation_date DATE PRIMARY KEY,
    high_temp_f DOUBLE PRECISION,
    low_temp_f DOUBLE PRECISION,
    mean_dewpoint_f DOUBLE PRECISION,
    rainfall_in DOUBLE PRECISION,
    peak_gust_mph DOUBLE PRECISION,
    mean_wind_mph DOUBLE PRECISION,
    peak_irradiance_w_m2 DOUBLE PRECISION,
    solar_energy_wh_m2 DOUBLE PRECISION,
    mean_relative_pressure_inhg DOUBLE PRECISION,
    lightning_strikes INTEGER,
    sample_count INTEGER NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
