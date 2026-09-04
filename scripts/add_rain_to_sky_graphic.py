import json
from pathlib import Path

path = Path("grafana/dashboards/weather.json")
dashboard = json.loads(path.read_text())
panel = next(p for p in dashboard["panels"] if p.get("id") == 22)

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
  ), 0) AS \"Rain rate\""""

css = panel["options"]["css"]
css = css.replace(
    '.sky-scene { width: 100%; height: 100%; display: block; }',
    '.sky-scene { width: 100%; height: 100%; display: block; }\n'
    '.rain-field { opacity: 0; stroke: rgba(220,240,255,.82); stroke-width: 3; stroke-linecap: round; transition: opacity .35s ease; }\n'
    '.rain-light { animation: rain-fall 1.15s linear infinite; }\n'
    '.rain-medium { animation: rain-fall .82s linear infinite; }\n'
    '.rain-heavy { animation: rain-fall .56s linear infinite; stroke-width: 4; }\n'
    '.sky-card[data-rain="light"] .rain-light { opacity: .52; }\n'
    '.sky-card[data-rain="moderate"] .rain-light { opacity: .58; }\n'
    '.sky-card[data-rain="moderate"] .rain-medium { opacity: .68; }\n'
    '.sky-card[data-rain="heavy"] .rain-light { opacity: .60; }\n'
    '.sky-card[data-rain="heavy"] .rain-medium { opacity: .75; }\n'
    '.sky-card[data-rain="heavy"] .rain-heavy { opacity: .88; }'
)
css = css.replace(
    '.sky-subtitle { margin-top: 4px; font-size: 13px; opacity: .82; }',
    '.rain-label { display: none; margin-top: 2px; font-size: 15px; font-weight: 600; opacity: .95; }\n'
    '.sky-card:not([data-rain="dry"]) .rain-label { display: block; }\n'
    '.sky-subtitle { margin-top: 4px; font-size: 13px; opacity: .82; }'
)
css = css.replace(
    '@keyframes drift-a {',
    '@keyframes rain-fall { from { transform: translateY(-36px); } to { transform: translateY(36px); } }\n'
    '@keyframes drift-a {'
)
panel["options"]["css"] = css

html = panel["options"]["html"]
html = html.replace(
    'id="sky-card" data-state="unavailable"',
    'id="sky-card" data-state="unavailable" data-rain="dry"'
)
rain_svg = '''\n    <g class="rain-field rain-light">\n      <line x1="110" y1="25" x2="98" y2="52"/><line x1="320" y1="68" x2="308" y2="95"/><line x1="540" y1="22" x2="528" y2="49"/><line x1="770" y1="74" x2="758" y2="101"/><line x1="1010" y1="30" x2="998" y2="57"/>\n      <line x1="205" y1="145" x2="193" y2="172"/><line x1="445" y1="125" x2="433" y2="152"/><line x1="675" y1="155" x2="663" y2="182"/><line x1="900" y1="132" x2="888" y2="159"/><line x1="1130" y1="150" x2="1118" y2="177"/>\n    </g>\n    <g class="rain-field rain-medium">\n      <line x1="55" y1="96" x2="42" y2="126"/><line x1="265" y1="18" x2="252" y2="48"/><line x1="390" y1="178" x2="377" y2="208"/><line x1="605" y1="82" x2="592" y2="112"/><line x1="835" y1="24" x2="822" y2="54"/><line x1="1080" y1="92" x2="1067" y2="122"/>\n      <line x1="155" y1="188" x2="142" y2="218"/><line x1="500" y1="92" x2="487" y2="122"/><line x1="720" y1="14" x2="707" y2="44"/><line x1="950" y1="184" x2="937" y2="214"/>\n    </g>\n    <g class="rain-field rain-heavy">\n      <line x1="15" y1="40" x2="0" y2="74"/><line x1="145" y1="80" x2="130" y2="114"/><line x1="350" y1="35" x2="335" y2="69"/><line x1="470" y1="165" x2="455" y2="199"/><line x1="635" y1="42" x2="620" y2="76"/><line x1="800" y1="160" x2="785" y2="194"/>\n      <line x1="925" y1="60" x2="910" y2="94"/><line x1="1165" y1="38" x2="1150" y2="72"/><line x1="250" y1="118" x2="235" y2="152"/><line x1="580" y1="185" x2="565" y2="219"/><line x1="1040" y1="170" x2="1025" y2="204"/>\n    </g>'''
html = html.replace('  </svg>', rain_svg + '\n  </svg>', 1)
html = html.replace(
    '<div class="sky-subtitle">Inferred from local solar irradiance</div>',
    '<div class="rain-label" id="rain-label"></div>\n    <div class="sky-subtitle">Inferred from local solar irradiance</div>'
)
panel["options"]["html"] = html

on_render = panel["options"]["onRender"]
on_render = on_render.replace(
    "const label = htmlNode.getElementById('sky-label');\nif (!card || !label) return;",
    "const label = htmlNode.getElementById('sky-label');\nconst rainLabel = htmlNode.getElementById('rain-label');\nif (!card || !label || !rainLabel) return;"
)
on_render += '''\n\nconst rainField = data.series?.flatMap(series => series.fields || []).find(candidate => candidate.name === 'Rain rate');\nlet rainRate = 0;\nif (rainField?.values?.length) {\n  const rainIndex = rainField.values.length - 1;\n  rainRate = Number(rainField.values.get ? rainField.values.get(rainIndex) : rainField.values[rainIndex]) || 0;\n}\n\nlet rainState = 'dry';\nlet rainText = '';\nif (rainRate > 0 && rainRate < 0.10) {\n  rainState = 'light';\n  rainText = 'Light rain';\n} else if (rainRate >= 0.10 && rainRate < 0.40) {\n  rainState = 'moderate';\n  rainText = 'Moderate rain';\n} else if (rainRate >= 0.40) {\n  rainState = 'heavy';\n  rainText = 'Heavy rain';\n}\n\ncard.dataset.rain = rainState;\nrainLabel.textContent = rainText ? `${rainText} · ${rainRate.toFixed(2)} in/hr` : '';\n'''
panel["options"]["onRender"] = on_render

path.write_text(json.dumps(dashboard, indent=2) + "\n")
