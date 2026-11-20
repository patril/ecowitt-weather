-- Re-runnable: new columns are nullable and existing non-null timestamps are preserved.
ALTER TABLE daily_weather_summary
    ADD COLUMN IF NOT EXISTS high_temp_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS low_temp_at TIMESTAMPTZ;

-- Backfill only missing timestamps. The half-open station-local day bounds
-- handle daylight saving time transitions correctly.
WITH missing AS (
    SELECT observation_date, high_temp_at, low_temp_at
    FROM daily_weather_summary
    WHERE high_temp_at IS NULL OR low_temp_at IS NULL
), extremes AS (
    SELECT
        d.observation_date,
        hi.observed_at AS high_temp_at,
        lo.observed_at AS low_temp_at
    FROM missing d
    LEFT JOIN LATERAL (
        SELECT w.observed_at
        FROM weather_observation w
        WHERE d.high_temp_at IS NULL
          AND w.observed_at >= (d.observation_date::timestamp AT TIME ZONE 'America/New_York')
          AND w.observed_at < ((d.observation_date + 1)::timestamp AT TIME ZONE 'America/New_York')
          AND w.outdoor_temp_f IS NOT NULL
        ORDER BY w.outdoor_temp_f DESC, w.observed_at ASC
        LIMIT 1
    ) hi ON TRUE
    LEFT JOIN LATERAL (
        SELECT w.observed_at
        FROM weather_observation w
        WHERE d.low_temp_at IS NULL
          AND w.observed_at >= (d.observation_date::timestamp AT TIME ZONE 'America/New_York')
          AND w.observed_at < ((d.observation_date + 1)::timestamp AT TIME ZONE 'America/New_York')
          AND w.outdoor_temp_f IS NOT NULL
        ORDER BY w.outdoor_temp_f ASC, w.observed_at ASC
        LIMIT 1
    ) lo ON TRUE
)
UPDATE daily_weather_summary d
SET
    high_temp_at = COALESCE(d.high_temp_at, e.high_temp_at),
    low_temp_at = COALESCE(d.low_temp_at, e.low_temp_at)
FROM extremes e
WHERE d.observation_date = e.observation_date
  AND ((d.high_temp_at IS NULL AND e.high_temp_at IS NOT NULL)
    OR (d.low_temp_at IS NULL AND e.low_temp_at IS NOT NULL));
