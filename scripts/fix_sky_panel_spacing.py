import json
from pathlib import Path

path = Path("grafana/dashboards/weather.json")
dashboard = json.loads(path.read_text())
panel = next(p for p in dashboard["panels"] if p.get("id") == 22)
css = panel["options"]["css"]
old = '.sky-card { position: relative; width: 100%; height: 100%; min-height: 170px; overflow: hidden;'
new = '.sky-card { position: relative; width: 100%; height: calc(100% - 22px); min-height: 0; margin-top: 22px; overflow: hidden;'
if old not in css:
    raise SystemExit("Expected sky-card CSS not found")
panel["options"]["css"] = css.replace(old, new, 1)
path.write_text(json.dumps(dashboard, indent=2) + "\n")
