'use strict';

const data = JSON.parse(document.getElementById('health-data').textContent);
const $ = id => document.getElementById(id);
const svgNS = 'http://www.w3.org/2000/svg';
const themes = {
  report: {name: 'Monthly Report', colors: {steps: '#3978bb', sleep: '#9073c4', resting_hr: '#d57955', hrv: '#7e9d42', workouts: '#809c45'}},
  recap: {name: 'Monthly Recap', colors: {steps: '#ae8938', sleep: '#b97160', resting_hr: '#6c9290', hrv: '#7c7caa', workouts: '#82914d'}},
  observatory: {name: 'Observatory', colors: {steps: '#e2b04f', sleep: '#a595ee', resting_hr: '#e57987', hrv: '#5fc5b4', workouts: '#729cf2'}},
  'field-notes': {name: 'Field Notes', colors: {steps: '#bd8332', sleep: '#8373ac', resting_hr: '#60889a', hrv: '#39795c', workouts: '#b36f58'}},
};
let activeTemplate = themes[data.template] ? data.template : 'report';
let range = 30;
const monthName = data.month.replace(/ \d{4}$/, '');
const year = data.month_start.slice(0, 4);
const elapsedDays = Number(data.through.slice(-2));
const chartKeys = ['steps', 'sleep', 'resting_hr', 'hrv'];
const descriptions = {
  steps: 'Daily totals · overlapping sources reconciled',
  sleep: 'Recorded sleep · hours per day',
  resting_hr: 'Daily mean · resting measurements',
  hrv: 'Daily mean · SDNN samples',
  workouts: 'Recorded active minutes · no inferred rest days',
};
const dateValue = text => new Date(text + 'T12:00:00Z');
const dayString = value => value.toISOString().slice(0, 10);
const dateLabel = text => dateValue(text).toLocaleDateString('en-US', {month: 'short', day: 'numeric', timeZone: 'UTC'});
const num = (value, digits = 0) => value === null ? '—' : value.toLocaleString('en-US', {maximumFractionDigits: digits, minimumFractionDigits: digits});
const color = key => themes[activeTemplate].colors[key];
const element = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
function svgElement(tag, attributes = {}, text) {
  const node = document.createElementNS(svgNS, tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}
function datesBetween(first, last) {
  const result = [];
  for (let d = dateValue(first); d <= dateValue(last); d.setUTCDate(d.getUTCDate() + 1)) result.push(dayString(d));
  return result;
}
function trendDays() {
  const start = dateValue(data.through);
  start.setUTCDate(start.getUTCDate() - range + 1);
  return datesBetween(dayString(start) < data.window_start ? data.window_start : dayString(start), data.through);
}
function monthEntries(key) {
  return Object.entries(data.series[key]).filter(([d]) => d >= data.month_start && d <= data.through);
}
const workouts = data.workouts.filter(w => w.date >= data.month_start && w.date <= data.through);

function changeText(key) {
  const result = dashboardCoverage.comparison(data, key);
  const unavailable = {
    'no-current': 'No measurements this month',
    'no-prior': 'No prior-month measurements',
    sparse: 'Limited coverage · change withheld',
    'zero-baseline': 'Prior value is zero · % unavailable',
  };
  if (result.reason !== 'available') return unavailable[result.reason];
  const sign = value => value > 0 ? '+' : value < 0 ? '−' : '';
  return sign(result.change) + num(Math.abs(result.change), 1) + '% vs prior month (' +
    sign(result.difference) + num(Math.abs(result.difference), data.metrics[key].decimals) + ' ' + data.metrics[key].unit + ')';
}
function periodLabel(period) {
  return dateLabel(period.first) + '–' + dateLabel(period.last);
}
function coverageLine(key, period) {
  const count = period.recorded + '/' + period.total;
  if (key === 'workouts') return count + ' days with workouts · ' + period.missing + ' without recorded workouts';
  return count + ' days recorded (' + num(period.fraction * 100) + '%) · ' + period.missing + ' missing';
}
function monthlyEvidence(key) {
  const periods = dashboardCoverage.monthly(data, key);
  const evidence = element('div', 'monthly-evidence');
  evidence.append(element('div', 'coverage-current', periodLabel(periods.current) + ': ' + coverageLine(key, periods.current)),
    element('div', 'coverage-prior', periodLabel(periods.previous) + ': ' + coverageLine(key, periods.previous)));
  if (key === 'workouts') {
    evidence.append(element('div', 'coverage-note', 'Recorded totals; export completeness unknown.'));
  } else {
    const sparse = dashboardCoverage.comparison(data, key).reason === 'sparse';
    evidence.append(element('div', sparse ? 'coverage-caution' : 'coverage-note', sparse ?
      'Change needs ≥7 recorded days and ≥80% coverage in both periods.' :
      'Average of recorded days; a recorded day may be incomplete.'));
  }
  return evidence;
}
function chartCoverage(key, days) {
  const period = dashboardCoverage.period(data.series[key], days[0], days.at(-1));
  const node = element('div', 'chart-coverage');
  node.append(element('strong', '', 'Chart · ' + periodLabel(period)), element('span', '', coverageLine(key, period)));
  return node;
}
function monthlyStats(key) {
  const meta = data.metrics[key], summary = data.summary[key];
  const node = element('div', 'chart-monthly-stats');
  const value = element('div', 'chart-monthly-value');
  value.append(element('strong', '', num(summary.value, meta.decimals)),
    element('span', '', (key === 'workouts' ? ' recorded total · ' : ' recorded-day average · ') + meta.unit));
  node.append(value, element('div', 'delta', changeText(key)), monthlyEvidence(key));
  return node;
}
function unitLabel(key) {
  return data.metrics[key].unit + (key === 'workouts' ? ' total' : key === 'steps' || key === 'sleep' ? ' / day' : ' daily avg');
}
function stat(key, cls = 'metric') {
  const meta = data.metrics[key], summary = data.summary[key];
  const node = element('article', cls);
  node.setAttribute('aria-label', meta.label);
  node.style.setProperty('--accent', color(key));
  node.dataset.metric = key;
  node.append(element('div', 'metric-label', meta.label));
  const value = element('div', 'value-line');
  value.append(element('strong', 'value', num(summary.value, meta.decimals)), element('span', 'unit', unitLabel(key)));
  node.append(value, element('div', 'delta', changeText(key)), monthlyEvidence(key));
  return node;
}
function demoBadge() {
  if (!data.demo) return;
  const notice = element('div', 'demo-notice', 'FICTIONAL SAMPLE DATA');
  notice.append(element('span', '', 'Same month. Different perspective.'));
  $('demo-slot').append(notice);
}
function comparison() {
  return 'Through ' + dateLabel(data.through) + ' · comparison ' + dateLabel(data.previous_start) + '–' + dateLabel(data.previous_end);
}
function controls() {
  const row = element('div', 'trendsbar');
  const heading = element('div');
  heading.append(element('h2', '', activeTemplate === 'observatory' ? 'SIGNAL HISTORY' : 'Your daily patterns'));
  const period = element('p'); period.id = 'trend-period'; period.setAttribute('aria-live', 'polite'); heading.append(period);
  const group = element('div', 'segments'); group.setAttribute('role', 'group'); group.setAttribute('aria-label', 'Trend range');
  for (const count of [7, 30, 90]) {
    const button = element('button', '', count + ' days');
    button.dataset.range = count;
    button.setAttribute('aria-pressed', String(range === count));
    button.addEventListener('click', () => {range = count; renderTrends();});
    group.append(button);
  }
  row.append(heading, group);
  return row;
}
function dataTable(key, days) {
  const meta = data.metrics[key], points = data.series[key];
  const recorded = days.filter(d => points[d] !== undefined).length;
  const details = element('details', 'chartdetails');
  details.append(element('summary', '', recorded + ' of ' + days.length + (key === 'workouts' ? ' days with workouts' : ' days recorded') + ' · Daily values'));
  const wrap = element('div', 'tablewrap'), table = element('table');
  table.append(element('caption', '', meta.label + ' · ' + meta.unit));
  const thead = element('thead'), row = element('tr');
  for (const title of ['Date', meta.unit]) {const th = element('th', '', title); th.scope = 'col'; row.append(th);}
  thead.append(row); table.append(thead);
  const tbody = element('tbody');
  for (const day of days) {
    const tr = element('tr');
    tr.append(element('td', '', day), element('td', '', points[day] === undefined ? 'No data' : num(points[day], meta.decimals)));
    tbody.append(tr);
  }
  table.append(tbody); wrap.append(table); details.append(wrap);
  return details;
}

function chartWidth(key) {
  const narrow = window.matchMedia('(max-width: 720px)').matches;
  const recapSingleColumn = window.matchMedia('(max-width: 540px)').matches;
  let fraction = narrow && (activeTemplate !== 'recap' || recapSingleColumn) ? 1 : .5;
  if (activeTemplate === 'observatory' && !narrow) {
    fraction = key === 'steps' ? 2 / 3 : key === 'sleep' ? 1 / 3 : key === 'workouts' ? 1 : .5;
  }
  return Math.max(130, $('charts').getBoundingClientRect().width * fraction - 42);
}
function timeChart(key, days, mode = 'line', compact = false) {
  const meta = data.metrics[key], values = days.map(d => data.series[key][d] ?? null);
  const known = values.filter(v => v !== null), plot = element('div', 'chart' + (compact ? ' compact-chart' : ''));
  if (!known.length) {plot.append(element('div', 'empty', 'No recorded data in this range')); return plot;}
  const W = chartWidth(key), H = compact ? 65 : activeTemplate === 'observatory' ? key === 'workouts' ? 120 : 138 : 155;
  const L = compact ? 4 : 38, R = 10, T = 12, B = compact ? 6 : 24;
  const IW = W - L - R, IH = H - T - B;
  const svg = svgElement('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': meta.label + ': ' + known.length + ' recorded days. Exact values in the daily table.'});
  const max = Math.max(...known), min = Math.min(...known), baseline = mode === 'bar' || mode === 'area';
  const low = baseline ? 0 : Math.max(0, Math.floor(min - (max - min) * .18 - 1));
  const high = baseline ? Math.max(1, Math.ceil(max * 1.1)) : Math.max(low + 2, Math.ceil(max + (max - min) * .18 + 1));
  const x = i => L + (i + .5) * IW / days.length;
  const y = v => T + IH - (v - low) / (high - low) * IH;
  if (!compact) {
    for (let i = 0; i <= 3; i++) {
      const v = low + (high - low) * i / 3, yy = y(v);
      svg.append(svgElement('line', {x1: L, x2: W - R, y1: yy, y2: yy, class: 'gridline'}));
      svg.append(svgElement('text', {x: L - 8, y: yy + 3, 'text-anchor': 'end', class: 'axis'}, v >= 1000 ? num(v / 1000, 1) + 'k' : num(v, key === 'sleep' ? 1 : 0)));
    }
  }
  if (mode === 'bar') {
    values.forEach((v, i) => {
      if (v === null) return;
      const mark = svgElement('rect', {x: x(i) - IW / days.length * .34, y: y(v), width: Math.max(1, IW / days.length * .68), height: Math.max(.8, T + IH - y(v)), rx: activeTemplate === 'observatory' ? 0 : 1.5, fill: color(key)});
      mark.append(svgElement('title', {}, days[i] + ': ' + num(v, meta.decimals) + ' ' + meta.unit)); svg.append(mark);
    });
  } else {
    let segments = [], segment = [];
    values.forEach((v, i) => {
      if (v === null) {if (segment.length) segments.push(segment); segment = []; return;}
      segment.push([x(i), y(v)]);
    });
    if (segment.length) segments.push(segment);
    for (const points of segments) {
      const path = 'M' + points.map(p => p.join(' ')).join(' L');
      if (mode === 'area') {
        const area = path + ` L${points.at(-1)[0]} ${T + IH} L${points[0][0]} ${T + IH} Z`;
        svg.append(svgElement('path', {d: area, fill: color(key), opacity: .16}));
      }
      if (mode !== 'dot') svg.append(svgElement('path', {d: path, fill: 'none', stroke: color(key), 'stroke-width': compact ? 2.5 : 2, 'stroke-linejoin': 'round'}));
    }
    values.forEach((v, i) => {
      if (v === null) return;
      if (mode === 'dot') svg.append(svgElement('line', {x1: x(i), x2: x(i), y1: y(v), y2: T + IH, stroke: color(key), opacity: .2}));
      const circle = svgElement('circle', {cx: x(i), cy: y(v), r: mode === 'dot' ? 3.3 : compact ? 1.6 : 2.3, fill: color(key)});
      circle.append(svgElement('title', {}, days[i] + ': ' + num(v, meta.decimals) + ' ' + meta.unit)); svg.append(circle);
    });
  }
  if (!compact) for (const i of [0, Math.floor((days.length - 1) / 2), days.length - 1]) {
    svg.append(svgElement('text', {x: x(i), y: H - 5, 'text-anchor': i === 0 ? 'start' : i === days.length - 1 ? 'end' : 'middle', class: 'axis'}, dateLabel(days[i])));
  }
  plot.append(svg);
  return plot;
}

function sleepDistribution(days) {
  const values = days.map(d => data.series.sleep[d]).filter(v => v !== undefined);
  if (!values.length) return timeChart('sleep', days);
  const bins = new Map();
  for (const value of values) {const bin = Math.floor(value); bins.set(bin, (bins.get(bin) || 0) + 1);}
  const first = Math.floor(Math.min(...values)), last = Math.floor(Math.max(...values));
  // Guard unusually large imported values from allocating an unbounded bin range.
  if (last - first > 24) return timeChart('sleep', days, 'bar');
  const keys = Array.from({length: last - first + 1}, (_, i) => first + i);
  const plot = element('div', 'chart distribution');
  const W = chartWidth('sleep');
  const svg = svgElement('svg', {viewBox: `0 0 ${W} 165`, role: 'img', 'aria-label': 'Sleep duration distribution. Bar heights count recorded days in each one-hour bin; exact daily values below.'});
  const max = Math.max(...bins.values()), width = (W - 60) / keys.length;
  for (const [i, bin] of keys.entries()) {
    const count = bins.get(bin) || 0, height = 110 * count / max;
    const rect = svgElement('rect', {x: 30 + i * width + width * .12, y: 127 - height, width: width * .76, height, rx: 3, fill: color('sleep'), opacity: .9});
    rect.append(svgElement('title', {}, `${bin}–${bin + 1} hours: ${count} recorded days`));
    svg.append(rect, svgElement('text', {x: 30 + (i + .5) * width, y: 117 - height, 'text-anchor': 'middle', class: 'axis'}, String(count)));
    svg.append(svgElement('text', {x: 30 + (i + .5) * width, y: 149, 'text-anchor': 'middle', class: 'axis'}, `${bin}–${bin + 1}h`));
  }
  plot.append(svg);
  return plot;
}

function chartPanel(key, days) {
  const meta = data.metrics[key], card = element('article', 'chart-card chart-' + key);
  card.style.setProperty('--accent', color(key));
  const head = element('div', 'charthead'), text = element('div');
  text.append(element('h3', '', meta.label), element('p', '', activeTemplate === 'report' && key === 'sleep' ? 'Sleep duration distribution · recorded days per bin' : descriptions[key]));
  head.append(text, element('span', 'chartunit', meta.unit)); card.append(head);
  if (activeTemplate === 'recap') card.prepend(stat(key, 'tile-stat'));
  const mode = key === 'steps' ? (activeTemplate === 'observatory' ? 'area' : 'bar') : key === 'sleep' ? 'bar' : key === 'hrv' && activeTemplate === 'report' ? 'dot' : 'line';
  card.append(activeTemplate === 'report' && key === 'sleep' ? sleepDistribution(days) : timeChart(key, days, mode, activeTemplate === 'recap'));
  card.append(chartCoverage(key, days));
  if (activeTemplate !== 'recap') card.append(monthlyStats(key));
  card.append(dataTable(key, days));
  return card;
}

function calendarPanel() {
  const card = element('article', 'calendar-panel');
  const head = element('div', 'calendar-head');
  head.append(element('h3', '', 'A month of movement'), element('span', '', workouts.length + ' recorded sessions'));
  const grid = element('div', 'calendar-grid'); grid.setAttribute('aria-label', 'Recorded workout days in the selected month');
  for (const day of datesBetween(data.month_start, data.through)) {
    const sessions = workouts.filter(w => w.date === day);
    const cell = element('div', 'calendar-day' + (sessions.length ? ' has-workout' : ''), String(Number(day.slice(-2))));
    const description = day + ': ' + (sessions.length ? sessions.length + ' recorded sessions, ' + num(sessions.reduce((s, w) => s + w.minutes, 0), 1) + ' minutes' : 'no recorded workout');
    cell.title = description; cell.setAttribute('aria-label', description); grid.append(cell);
  }
  card.append(head, grid, element('p', 'calendar-key', 'Filled = recorded workout · outlined = no recorded workout, not necessarily a rest day'));
  return card;
}
function coveragePanel() {
  const panel = element('article', 'coverage-panel');
  panel.append(element('h3', '', 'HOW MUCH OF THE MONTH IS RECORDED'));
  for (const key of chartKeys) {
    const row = element('div', 'coverage-row'), track = element('div', 'coverage-track'), fill = element('div');
    fill.style.width = (100 * data.summary[key].days / elapsedDays) + '%'; fill.style.background = color(key); track.append(fill);
    row.append(element('span', '', data.metrics[key].label), track, element('b', '', data.summary[key].days + '/' + elapsedDays)); panel.append(row);
  }
  panel.append(element('p', '', 'Recorded-day coverage, not a health score or goal.'));
  return panel;
}
function heatmap(days) {
  const panel = element('article', 'heatmap-panel');
  panel.append(element('h3', '', 'DAILY SIGNAL MAP'), element('p', '', 'Each row uses its own recorded range. Outlines indicate missing data.'));
  const coverageLabels = chartKeys.map(key => data.metrics[key].label + ': ' +
    coverageLine(key, dashboardCoverage.period(data.series[key], days[0], days.at(-1)))).join('. ');
  const svg = svgElement('svg', {viewBox: '0 0 1000 176', role: 'img', 'aria-label': 'Daily metric heatmap. Each row is independently scaled. ' + coverageLabels + '. Exact values in each chart’s table.'});
  const width = 708 / days.length;
  chartKeys.forEach((key, row) => {
    const values = days.map(d => data.series[key][d]), known = values.filter(v => v !== undefined);
    const low = Math.min(...known), high = Math.max(...known);
    svg.append(svgElement('text', {x: 0, y: 28 + row * 33, class: 'axis heat-label'}, {steps: 'Steps', sleep: 'Sleep', resting_hr: 'Resting HR', hrv: 'HRV'}[key]));
    svg.append(svgElement('text', {x: 845, y: 19 + row * 33, class: 'axis heat-coverage'}, known.length + '/' + days.length + ' recorded'),
      svgElement('text', {x: 845, y: 33 + row * 33, class: 'axis heat-coverage'}, (days.length - known.length) + ' missing'));
    values.forEach((v, i) => {
      const missing = v === undefined;
      const rect = svgElement('rect', {x: 118 + i * width, y: 9 + row * 33, width: Math.max(1, width - 2), height: 24, rx: 1,
        fill: missing ? 'none' : color(key), 'fill-opacity': missing ? 0 : high === low ? .7 : .2 + .8 * (v - low) / (high - low), stroke: missing ? 'var(--line)' : 'none'});
      rect.append(svgElement('title', {}, days[i] + ' · ' + data.metrics[key].label + ': ' + (missing ? 'No data' : num(v, data.metrics[key].decimals) + ' ' + data.metrics[key].unit))); svg.append(rect);
    });
  });
  svg.append(svgElement('text', {x: 118, y: 163, class: 'axis'}, dateLabel(days[0])), svgElement('text', {x: 826, y: 163, 'text-anchor': 'end', class: 'axis'}, dateLabel(days.at(-1))));
  const scroll = element('div', 'heatmap-scroll');
  scroll.tabIndex = 0; scroll.setAttribute('aria-label', 'Daily signal map; scroll horizontally on small screens');
  scroll.append(svg); panel.append(scroll);
  return panel;
}
function training() {
  const panel = element('article', 'training');
  panel.append(element('h3', '', 'Training log'), element('p', '', workouts.length ? `${workouts.length} sessions · ${num(data.summary.workouts.value)} active minutes this month` : 'No recorded workouts this month'));
  for (const w of workouts.slice(-5).reverse()) {
    const row = element('div', 'session');
    row.append(element('span', 'sessiondate', dateLabel(w.date)), element('span', '', w.activity.replace(/([a-z])([A-Z])/g, '$1 $2')), element('span', 'sessionduration', num(w.minutes, 1) + ' min')); panel.append(row);
  }
  panel.append(element('div', 'coverage', 'Latest five sessions · ' + changeText('workouts')));
  return panel;
}
function notes() {
  const details = element('details', 'notes');
  details.append(element('summary', '', 'Sources, coverage & calculation notes'));
  details.append(element('p', '', 'Sources: ' + data.sources.join(', ')));
  const copy = [
    'Missing days stay missing. Averages use recorded days only; workout minutes are a total. Comparisons cover the same elapsed days in the prior month, capped at its end. Monthly summaries stay fixed when the chart range changes.',
    'Daily-metric changes are displayed only when each comparison period has at least 7 recorded days and 80% recorded-day coverage. This is a display rule, not statistical confidence or evidence of a trend. Coverage counts days with at least one usable value, not raw samples or device wear time; a recorded day may be incomplete.',
    'Workout comparisons use recorded minute totals. Days without recorded workouts do not prove missing data or rest; export completeness cannot be inferred from workout-day counts.',
    'Steps reconcile overlapping sources in the order Health, Apple Watch, iPhone, then other sources. Heart measurements at identical intervals are reconciled; other samples contribute to daily means. Use --source to restrict sources when generating the file; saved preferences are not read.',
    'Sleep is grouped by each record’s end date, with in-bed time excluded. Workouts use valid active duration with elapsed time as a fallback. Exact matching intervals and activity types count once. Dates use export offsets.',
    'HRV is mean daily SDNN, not a recovery score. Charts show observations, not diagnoses or evidence that a habit caused a change.',
  ];
  for (const text of copy) details.append(element('p', '', text));
  for (const warning of data.warnings) details.append(element('p', 'warning', warning));
  return details;
}

function renderTrends() {
  const days = trendDays();
  $('trend-period').textContent = dateLabel(days[0]) + ' – ' + dateLabel(days.at(-1)) + ' · ' + days.length + ' days';
  for (const button of document.querySelectorAll('[data-range]')) button.setAttribute('aria-pressed', String(Number(button.dataset.range) === range));
  const panels = chartKeys.map(key => chartPanel(key, days));
  $('charts').replaceChildren(...panels);
  if (activeTemplate === 'observatory') {
    const grid = $('charts');
    grid.insertBefore(heatmap(days), panels[2]);
    const coverage = coveragePanel(); coverage.classList.add('observatory-coverage'); grid.insertBefore(coverage, panels[2]);
    const workout = element('article', 'chart-card chart-workouts');
    workout.append(element('h3', '', 'WORKOUT VOLUME'), element('p', 'chart-subtitle', descriptions.workouts), timeChart('workouts', days, 'bar'), chartCoverage('workouts', days), monthlyStats('workouts'), dataTable('workouts', days)); grid.append(workout);
  }
}

function render() {
  document.body.dataset.template = activeTemplate;
  document.documentElement.style.colorScheme = activeTemplate === 'observatory' ? 'dark' : 'light';
  $('template').value = activeTemplate;
  document.title = data.month + ' · ' + themes[activeTemplate].name + ' · healthai';
  // Layout skeletons contain only fixed markup. Export strings are assigned via
  // textContent in the renderers below, never inserted as markup.
  $('dashboard').innerHTML = `
    <div id="demo-slot"></div>
    <header class="report-header"><div><div class="eyebrow" id="eyebrow"></div><h1 id="title"></h1><p id="subtitle"></p></div><div class="edition"><span id="month"></span><small id="period"></small></div></header>
    <div id="intro"></div><div id="metrics" class="metrics"></div>
    <div id="controls"></div><div id="charts" class="charts"></div>
    <div id="supplement" class="supplement"></div><div id="method"></div>`;
  demoBadge();
  $('period').textContent = 'Through ' + dateLabel(data.through);
  $('month').textContent = data.month;
  $('controls').append(controls());
  if (activeTemplate === 'report') {
    $('eyebrow').textContent = 'HEALTHAI / MONTHLY REPORT';
    $('title').textContent = 'Your health summary.';
    $('subtitle').textContent = 'A month of movement, rest, and everything in between.';
    $('intro').append(element('p', 'comparison', comparison()));
    $('metrics').hidden = true;
    $('supplement').append(calendarPanel(), coveragePanel());
    const close = element('div', 'report-close');
    close.append(element('div', 'eyebrow', 'THE MONTH, RECORDED'), element('h2', '', data.summary.steps.days + ' days of steps. ' + data.summary.sleep.days + ' days of sleep.'), element('p', '', workouts.length + ' workout sessions · ' + (data.summary.workouts.value === null ? 'No recorded workout time' : num(data.summary.workouts.value) + ' active minutes') + ' · Your next report adds the next chapter.'));
    $('supplement').append(close);
    const sessions = element('details', 'report-sessions');
    sessions.append(element('summary', '', 'Recent workouts · ' + changeText('workouts')), training());
    $('supplement').append(sessions);
  } else if (activeTemplate === 'recap') {
    $('eyebrow').textContent = 'HEALTHAI — A PERSONAL ALMANAC';
    $('title').textContent = monthName.toUpperCase();
    $('subtitle').textContent = year + ' / YOUR MONTH IN NUMBERS';
    $('month').textContent = String(elapsedDays).padStart(2, '0');
    $('period').textContent = 'calendar days · through ' + dateLabel(data.through);
    const banner = element('div', 'recap-banner');
    banner.append(element('span', 'eyebrow', 'THE BIG PICTURE'));
    const total = monthEntries('steps').reduce((sum, [, v]) => sum + v, 0);
    banner.append(element('strong', '', data.summary.steps.value === null ? 'Your month, recorded.' : num(total) + ' steps. One month.'), element('p', '', 'Across ' + data.summary.steps.days + ' recorded days · ' + workouts.length + ' workout sessions · through ' + dateLabel(data.through)));
    $('intro').append(banner);
    $('metrics').hidden = true;
    const movement = element('div', 'recap-movement');
    movement.append(stat('workouts'), calendarPanel());
    $('supplement').append(movement, training());
    $('method').append(element('p', 'comparison', comparison()));
  } else if (activeTemplate === 'observatory') {
    $('eyebrow').textContent = 'PERSONAL TELEMETRY / APPLE HEALTH';
    $('title').textContent = 'Observatory';
    $('subtitle').textContent = 'MONTHLY OVERVIEW · ' + data.month.toUpperCase();
    $('month').textContent = '● SNAPSHOT';
    $('period').textContent = 'Latest record ' + data.latest;
    for (const key of Object.keys(data.metrics)) $('metrics').append(stat(key));
    $('intro').append(element('p', 'comparison', comparison()));
    $('supplement').append(training());
  } else {
    $('eyebrow').textContent = 'YOUR PERSONAL HEALTH JOURNAL';
    $('title').textContent = 'Your health, in perspective.';
    $('subtitle').textContent = 'A quieter view of your daily patterns. Small changes, seen over time.';
    $('intro').append(element('p', 'comparison', comparison()));
    for (const key of Object.keys(data.metrics)) $('metrics').append(stat(key));
    $('supplement').append(training(), coveragePanel());
  }
  $('method').append(notes());
  $('freshness').textContent = (data.demo ? 'Fictional demo' : 'Export snapshot') + ' · generated ' + data.generated_at.slice(0, 10) + '. Regenerate from a newer export to refresh.';
  renderTrends();
}
$('template').addEventListener('change', event => {activeTemplate = event.target.value; render();});
$('print').addEventListener('click', () => window.print());
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(renderTrends, 100);
});
render();
