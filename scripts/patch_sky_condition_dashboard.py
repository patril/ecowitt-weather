import json
from pathlib import Path

path = Path('grafana/dashboards/weather.json')
dashboard = json.loads(path.read_text())

html = '''
<div class="sky-card" id="sky-card" data-state="unavailable">
  <svg class="sky-scene" viewBox="0 0 1200 220" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="day-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#4da6ff"/><stop offset="100%" stop-color="#cfeeff"/>
      </linearGradient>
      <linearGradient id="night-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#07152f"/><stop offset="100%" stop-color="#182b4d"/>
      </linearGradient>
      <filter id="soft-glow"><feGaussianBlur stdDeviation="7"/></filter>
    </defs>
    <rect class="sky-bg day-bg" width="1200" height="220" fill="url(#day-sky)"/>
    <rect class="sky-bg night-bg" width="1200" height="220" fill="url(#night-sky)"/>
    <g class="stars">
      <circle cx="90" cy="50" r="2"/><circle cx="180" cy="86" r="1.5"/><circle cx="300" cy="42" r="2"/>
      <circle cx="430" cy="74" r="1.5"/><circle cx="760" cy="48" r="2"/><circle cx="900" cy="85" r="1.5"/>
      <circle cx="1030" cy="43" r="2"/><circle cx="1120" cy="76" r="1.5"/>
    </g>
    <g class="sun" transform="translate(230 88)">
      <circle class="sun-glow" r="48" filter="url(#soft-glow)"/><circle class="sun-core" r="34"/>
      <g class="rays">
        <line x1="0" y1="-58" x2="0" y2="-76"/><line x1="0" y1="58" x2="0" y2="76"/>
        <line x1="-58" y1="0" x2="-76" y2="0"/><line x1="58" y1="0" x2="76" y2="0"/>
        <line x1="-41" y1="-41" x2="-54" y2="-54"/><line x1="41" y1="41" x2="54" y2="54"/>
        <line x1="41" y1="-41" x2="54" y2="-54"/><line x1="-41" y1="41" x2="-54" y2="54"/>
      </g>
    </g>
    <g class="moon" transform="translate(245 82)"><circle r="34"/><circle class="moon-cut" cx="14" cy="-8" r="33"/></g>
    <g class="cloud cloud-a" transform="translate(455 106)">
      <ellipse cx="0" cy="18" rx="92" ry="32"/><circle cx="-42" cy="0" r="38"/><circle cx="15" cy="-18" r="50"/><circle cx="58" cy="5" r="35"/>
    </g>
    <g class="cloud cloud-b" transform="translate(770 120) scale(.8)">
      <ellipse cx="0" cy="18" rx="92" ry="32"/><circle cx="-42" cy="0" r="38"/><circle cx="15" cy="-18" r="50"/><circle cx="58" cy="5" r="35"/>
    </g>
    <g class="cloud cloud-c" transform="translate(1010 92) scale(.65)">
      <ellipse cx="0" cy="18" rx="92" ry="32"/><circle cx="-42" cy="0" r="38"/><circle cx="15" cy="-18" r="50"/><circle cx="58" cy="5" r="35"/>
    </g>
    <path class="horizon" d="M0 188 C180 165 315 199 470 180 C640 160 785 199 950 177 C1065 162 1140 172 1200 166 L1200 220 L0 220 Z"/>
  </svg>
  <div class="sky-copy">
    <div class="sky-label" id="sky-label">Unavailable</div>
    <div class="sky-subtitle">Inferred from local solar irradiance</div>
  </div>
</div>
'''.strip()

css = '''
.sky-card { position: relative; width: 100%; height: 100%; min-height: 170px; overflow: hidden; border-radius: 8px; color: white; font-family: Inter, "Helvetica Neue", Arial, sans-serif; }
.sky-scene { width: 100%; height: 100%; display: block; }
.sky-bg { transition: opacity .8s ease, fill .8s ease; }
.night-bg, .stars, .moon { opacity: 0; }
.stars { fill: #fff; }
.sun { transition: opacity .6s ease, transform .8s ease; transform-origin: 230px 88px; }
.sun-core, .sun-glow { fill: #ffd45c; }
.sun-glow { opacity: .42; }
.rays { stroke: #ffe9a8; stroke-width: 5; stroke-linecap: round; }
.moon { fill: #f4f1d5; transition: opacity .8s ease; }
.moon-cut { fill: #0b1d39; }
.cloud { fill: #f7fbff; opacity: 0; transition: opacity .7s ease, fill .7s ease; }
.cloud-a { animation: drift-a 18s ease-in-out infinite alternate; }
.cloud-b { animation: drift-b 22s ease-in-out infinite alternate; }
.cloud-c { animation: drift-c 26s ease-in-out infinite alternate; }
.horizon { fill: rgba(25, 70, 63, .32); }
.sky-copy { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -48%); text-align: center; text-shadow: 0 2px 9px rgba(0,0,0,.45); pointer-events: none; }
.sky-label { font-size: clamp(26px, 3vw, 46px); font-weight: 650; letter-spacing: .01em; }
.sky-subtitle { margin-top: 4px; font-size: 13px; opacity: .82; }
.sky-card[data-state="clear"] .sun { opacity: 1; }
.sky-card[data-state="variable-clouds"] .cloud-a, .sky-card[data-state="variable-clouds"] .cloud-b { opacity: .94; }
.sky-card[data-state="variable-clouds"] .sun { opacity: .92; }
.sky-card[data-state="cloud-obscured"] .cloud-a, .sky-card[data-state="cloud-obscured"] .cloud-b, .sky-card[data-state="cloud-obscured"] .cloud-c { opacity: .98; }
.sky-card[data-state="cloud-obscured"] .sun { opacity: .38; }
.sky-card[data-state="heavy-cloud"] .day-bg { fill: #718093; }
.sky-card[data-state="heavy-cloud"] .cloud-a, .sky-card[data-state="heavy-cloud"] .cloud-b, .sky-card[data-state="heavy-cloud"] .cloud-c { opacity: 1; fill: #cbd3dc; }
.sky-card[data-state="heavy-cloud"] .sun { opacity: .08; }
.sky-card[data-state="night-low-sun"] .day-bg { opacity: 0; }
.sky-card[data-state="night-low-sun"] .night-bg, .sky-card[data-state="night-low-sun"] .stars, .sky-card[data-state="night-low-sun"] .moon { opacity: 1; }
.sky-card[data-state="night-low-sun"] .sun, .sky-card[data-state="night-low-sun"] .cloud { opacity: 0; }
.sky-card[data-state="unavailable"] .day-bg { fill: #515966; }
.sky-card[data-state="unavailable"] .sun, .sky-card[data-state="unavailable"] .cloud { opacity: .12; }
@keyframes drift-a { from { transform: translate(430px,106px); } to { transform: translate(485px,106px); } }
@keyframes drift-b { from { transform: translate(750px,120px) scale(.8); } to { transform: translate(805px,120px) scale(.8); } }
@keyframes drift-c { from { transform: translate(990px,92px) scale(.65); } to { transform: translate(1035px,92px) scale(.65); } }
'''.strip()

on_render = '''
const card = htmlNode.getElementById('sky-card');
const label = htmlNode.getElementById('sky-label');
if (!card || !label) return;

const field = data.series?.flatMap(series => series.fields || []).find(candidate => candidate.name === 'Sky condition');
let condition = 'Unavailable';
if (field?.values?.length) {
  const index = field.values.length - 1;
  condition = field.values.get ? field.values.get(index) : field.values[index];
}
condition = condition || 'Unavailable';

const states = {
  'Clear': 'clear',
  'Variable clouds': 'variable-clouds',
  'Cloud-obscured': 'cloud-obscured',
  'Heavy cloud': 'heavy-cloud',
  'Night / low sun': 'night-low-sun',
  'Unavailable': 'unavailable'
};
card.dataset.state = states[condition] || 'unavailable';
label.textContent = condition;
'''.strip()

for panel in dashboard['panels']:
    if panel.get('id') == 22:
        panel['type'] = 'gapit-htmlgraphics-panel'
        panel['pluginVersion'] = '2.2.3'
        panel['gridPos']['h'] = 5
        panel['options'] = {
            'add100Percentage': True,
            'centerAlignContent': True,
            'overflow': 'hidden',
            'useGrafanaScrollbar': False,
            'SVGBaseFix': True,
            'codeData': '{}',
            'rootCSS': '',
            'css': css,
            'html': html,
            'renderOnMount': True,
            'onRender': on_render,
            'dynamicHtmlGraphics': False,
            'dynamicData': False,
            'dynamicFieldDisplayValues': False,
            'dynamicProps': False,
            'panelupdateOnMount': True,
            'onInitOnResize': False,
            'onInit': ''
        }
    elif panel.get('gridPos', {}).get('y', 0) >= 13:
        panel['gridPos']['y'] += 2

path.write_text(json.dumps(dashboard, indent=2) + '\n')
