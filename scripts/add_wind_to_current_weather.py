import json
from pathlib import Path

path = Path("grafana/dashboards/weather.json")
dashboard = json.loads(path.read_text())
panel = next(p for p in dashboard["panels"] if p.get("id") == 22)

panel["title"] = "Current Weather"

panel["targets"][0]["rawSql"] = """SELECT
  COALESCE((
    SELECT CASE WHEN observed_at >= NOW() - INTERVAL '2 minutes' THEN condition ELSE 'Unavailable' END
    FROM sky_condition_observation
    ORDER BY observed_at DESC
    LIMIT 1
  ), 'Unavailable') AS \"Sky condition\",
  COALESCE((
    SELECT CASE WHEN observed_at >= NOW() - INTERVAL '2 minutes' THEN COALESCE(rain_rate_in_hr, 0) ELSE 0 END
    FROM rain_observation
    WHERE source = 'wh40'
    ORDER BY observed_at DESC
    LIMIT 1
  ), 0) AS \"Rain rate\",
  COALESCE((
    SELECT CASE WHEN observed_at >= NOW() - INTERVAL '2 minutes' THEN COALESCE(wind_speed_mph, 0) ELSE 0 END
    FROM weather_observation
    ORDER BY observed_at DESC
    LIMIT 1
  ), 0) AS \"Wind speed\",
  COALESCE((
    SELECT CASE WHEN observed_at >= NOW() - INTERVAL '2 minutes' THEN wind_direction_deg ELSE NULL END
    FROM weather_observation
    ORDER BY observed_at DESC
    LIMIT 1
  ), 0) AS \"Wind direction\""""

css = panel["options"]["css"]
css = css.replace(
    '.cloud-a { animation: drift-a 18s ease-in-out infinite alternate; }\n.cloud-b { animation: drift-b 22s ease-in-out infinite alternate; }\n.cloud-c { animation: drift-c 26s ease-in-out infinite alternate; }',
    '.cloud-a { animation: drift-a var(--cloud-a-duration, 18s) ease-in-out infinite alternate; }\n.cloud-b { animation: drift-b var(--cloud-b-duration, 22s) ease-in-out infinite alternate; }\n.cloud-c { animation: drift-c var(--cloud-c-duration, 26s) ease-in-out infinite alternate; }'
)
css = css.replace(
    '.rain-field { opacity: 0; stroke: rgba(220,240,255,.82); stroke-width: 3; stroke-linecap: round; transition: opacity .35s ease; }',
    '.rain-layer { transform-box: fill-box; transform-origin: center; transition: transform .35s ease; }\n.rain-field { opacity: 0; stroke: rgba(220,240,255,.82); stroke-width: 3; stroke-linecap: round; transition: opacity .35s ease; }'
)
panel["options"]["css"] = css

html = panel["options"]["html"]
html = html.replace('<g class="rain-field rain-light">', '<g class="rain-layer" id="rain-layer">\n    <g class="rain-field rain-light">', 1)
html = html.replace('    </g>\n  </svg>', '    </g>\n    </g>\n  </svg>', 1)
panel["options"]["html"] = html

on_render = panel["options"]["onRender"]
on_render += '''\n\nconst windSpeedField = data.series?.flatMap(series => series.fields || []).find(candidate => candidate.name === 'Wind speed');\nconst windDirectionField = data.series?.flatMap(series => series.fields || []).find(candidate => candidate.name === 'Wind direction');\nlet windSpeed = 0;\nlet windDirection = 0;\nif (windSpeedField?.values?.length) {\n  const i = windSpeedField.values.length - 1;\n  windSpeed = Number(windSpeedField.values.get ? windSpeedField.values.get(i) : windSpeedField.values[i]) || 0;\n}\nif (windDirectionField?.values?.length) {\n  const i = windDirectionField.values.length - 1;\n  windDirection = Number(windDirectionField.values.get ? windDirectionField.values.get(i) : windDirectionField.values[i]) || 0;\n}\n\nconst windFactor = Math.max(0, Math.min(1, windSpeed / 20));\nconst cloudFactor = Math.max(0.35, 1 - 0.65 * windFactor);\ncard.style.setProperty('--cloud-a-duration', `${(18 * cloudFactor).toFixed(2)}s`);\ncard.style.setProperty('--cloud-b-duration', `${(22 * cloudFactor).toFixed(2)}s`);\ncard.style.setProperty('--cloud-c-duration', `${(26 * cloudFactor).toFixed(2)}s`);\n\n// Meteorological direction is where the wind comes FROM. Convert it to the\n// horizontal component of where the air is moving TO for the scene.\nconst towardRadians = ((windDirection + 180) % 360) * Math.PI / 180;\nconst horizontalComponent = Math.sin(towardRadians);\nconst cloudDirection = horizontalComponent < 0 ? 'alternate-reverse' : 'alternate';\nfor (const cloud of htmlNode.querySelectorAll('.cloud-a, .cloud-b, .cloud-c')) {\n  cloud.style.animationDirection = cloudDirection;\n}\n\nconst rainLayer = htmlNode.getElementById('rain-layer');\nif (rainLayer) {\n  const rainTiltDegrees = Math.max(-24, Math.min(24, horizontalComponent * windFactor * 24));\n  rainLayer.setAttribute('transform', `skewX(${rainTiltDegrees.toFixed(1)})`);\n}\n'''
panel["options"]["onRender"] = on_render

path.write_text(json.dumps(dashboard, indent=2) + "\n")
