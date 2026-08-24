CREATE TABLE IF NOT EXISTS weather_observation (
    observed_at             TIMESTAMPTZ PRIMARY KEY,
    outdoor_temp_f          DOUBLE PRECISION,
    outdoor_humidity_pct    DOUBLE PRECISION,
    feels_like_f            DOUBLE PRECISION,
    dewpoint_f              DOUBLE PRECISION,
    wind_speed_mph          DOUBLE PRECISION,
    wind_gust_mph           DOUBLE PRECISION,
    daily_max_wind_mph      DOUBLE PRECISION,
    wind_direction_deg      DOUBLE PRECISION,
    solar_w_m2              DOUBLE PRECISION,
    uv_index                DOUBLE PRECISION,
    indoor_temp_f           DOUBLE PRECISION,
    indoor_humidity_pct     DOUBLE PRECISION,
    absolute_pressure_inhg  DOUBLE PRECISION,
    relative_pressure_inhg  DOUBLE PRECISION,
    raw_json                JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_weather_observation_observed_at
    ON weather_observation (observed_at DESC);

CREATE TABLE IF NOT EXISTS rain_observation (
    observed_at          TIMESTAMPTZ NOT NULL,
    source               TEXT NOT NULL CHECK (source IN ('wh40', 'ws90')),
    event_rain_in        DOUBLE PRECISION,
    rain_rate_in_hr      DOUBLE PRECISION,
    daily_rain_in        DOUBLE PRECISION,
    weekly_rain_in       DOUBLE PRECISION,
    monthly_rain_in      DOUBLE PRECISION,
    yearly_rain_in       DOUBLE PRECISION,
    battery_level        INTEGER,
    battery_voltage_v    DOUBLE PRECISION,
    ws90_cap_voltage_v   DOUBLE PRECISION,
    ws90_firmware        TEXT,
    raw_json             JSONB NOT NULL,
    PRIMARY KEY (observed_at, source)
);

CREATE INDEX IF NOT EXISTS idx_rain_observation_source_time
    ON rain_observation (source, observed_at DESC);

CREATE TABLE IF NOT EXISTS lightning_observation (
    observed_at          TIMESTAMPTZ PRIMARY KEY,
    last_strike_at_local TIMESTAMP,
    distance_miles       DOUBLE PRECISION,
    cumulative_count     BIGINT,
    battery_level        INTEGER,
    raw_json             JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lightning_observation_observed_at
    ON lightning_observation (observed_at DESC);
