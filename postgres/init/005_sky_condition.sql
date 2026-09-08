CREATE TABLE IF NOT EXISTS sky_condition_observation (
    observed_at TIMESTAMPTZ PRIMARY KEY REFERENCES weather_observation(observed_at) ON DELETE CASCADE,
    condition TEXT NOT NULL,
    clear_sky_index DOUBLE PRECISION,
    variability DOUBLE PRECISION,
    clear_sky_w_m2 DOUBLE PRECISION
);
