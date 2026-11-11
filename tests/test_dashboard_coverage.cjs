// Run with node --test tests/test_dashboard_coverage.cjs.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const coverage = vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/healthai/dashboard_coverage.js'), 'utf8') + '\ndashboardCoverage;');

function fixture(current = 31, previous = 30, key = 'steps', value = 110, old = 100) {
  const points = {};
  for (const [month, count] of [['10', current], ['09', previous]]) {
    for (let i = 1; i <= count; i++) points[`2026-${month}-${String(i).padStart(2, '0')}`] = 0;
  }
  return {month_start: '2026-10-01', through: '2026-10-31', previous_start: '2026-09-01', previous_end: '2026-09-30',
    series: {[key]: points}, summary: {[key]: {value, previous: old}}};
}

test('coverage counts recorded zero values, excludes other dates, and uses inclusive calendar days', () => {
  const p = coverage.period({'2026-10-01': 0, '2026-10-31': 100, '2026-09-30': 5}, '2026-10-01', '2026-10-31');
  assert.equal(p.recorded, 2);
  assert.equal(p.total, 31);
  assert.equal(p.missing, 29);
});

test('well-covered periods expose signed percentage and absolute difference', () => {
  const result = coverage.comparison(fixture(), 'steps');
  assert.equal(result.reason, 'available');
  assert.equal(result.change, 10);
  assert.equal(result.difference, 10);
  assert.equal(coverage.comparison(fixture(31, 30, 'steps', 90), 'steps').difference, -10);
});

test('sparse current or prior month withholds the delta, even when a numeric average exists', () => {
  for (const counts of [[2, 30], [31, 1], [24, 30], [31, 23]]) {
    assert.equal(coverage.comparison(fixture(...counts), 'steps').reason, 'sparse');
  }
  assert.equal(coverage.comparison(fixture(25, 24), 'steps').reason, 'available');
});

test('a six-day month-to-date period does not masquerade as an established comparison', () => {
  const d = fixture(6, 6);
  d.through = '2026-10-06'; d.previous_end = '2026-09-06';
  assert.equal(coverage.comparison(d, 'steps').reason, 'sparse');
  const week = fixture(7, 7);
  week.through = '2026-10-07'; week.previous_end = '2026-09-07';
  assert.equal(coverage.comparison(week, 'steps').reason, 'available');
});

test('partial months and leap February use their own denominators', () => {
  const d = fixture(11, 11);
  d.through = '2026-10-11'; d.previous_end = '2026-09-11';
  assert.equal(coverage.monthly(d, 'steps').current.total, 11);
  assert.equal(coverage.monthly(d, 'steps').previous.missing, 0);
  assert.equal(coverage.period({}, '2024-02-01', '2024-02-29').total, 29);
  assert.equal(coverage.period({}, '2026-02-01', '2026-02-28').total, 28);
});

test('missing periods and zero baselines never produce misleading percentages', () => {
  assert.equal(coverage.comparison(fixture(0, 30, 'steps', null), 'steps').reason, 'no-current');
  assert.equal(coverage.comparison(fixture(31, 0, 'steps', 110, null), 'steps').reason, 'no-prior');
  assert.equal(coverage.comparison(fixture(31, 30, 'steps', 110, 0), 'steps').reason, 'zero-baseline');
  assert.equal(coverage.comparison(fixture(31, 30, 'steps', 0, 100), 'steps').change, -100);
});

test('workout events are not subject to the daily recording coverage threshold', () => {
  const result = coverage.comparison(fixture(2, 1, 'workouts', 90, 45), 'workouts');
  assert.equal(result.reason, 'available');
  assert.equal(result.change, 100);
  assert.equal(result.difference, 45);
});

test('changing the chart window does not change monthly comparison coverage', () => {
  const d = fixture();
  assert.equal(coverage.period(d.series.steps, '2026-10-25', '2026-10-31').total, 7);
  assert.equal(coverage.period(d.series.steps, '2026-08-03', '2026-10-31').total, 90);
  assert.equal(coverage.monthly(d, 'steps').current.total, 31);
  assert.equal(coverage.monthly(d, 'steps').previous.total, 30);
});
