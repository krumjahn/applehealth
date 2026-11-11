'use strict';

// Display eligibility, not a measure of statistical confidence or device wear.
const dashboardCoverage = {
  period(points, first, last) {
    const total = Math.round((new Date(last + 'T12:00:00Z') - new Date(first + 'T12:00:00Z')) / 86400000) + 1;
    const recorded = Object.keys(points).filter(day => day >= first && day <= last).length;
    return {first, last, total, recorded, missing: total - recorded, fraction: recorded / total};
  },
  monthly(data, key) {
    return {
      current: this.period(data.series[key], data.month_start, data.through),
      previous: this.period(data.series[key], data.previous_start, data.previous_end),
    };
  },
  comparison(data, key) {
    const {current, previous} = this.monthly(data, key);
    const summary = data.summary[key];
    if (summary.value === null || !current.recorded) return {reason: 'no-current'};
    if (summary.previous === null || !previous.recorded) return {reason: 'no-prior'};
    // Workout days are events, not proof of export coverage. Rest days must not
    // be classified as missing health measurements or fail the daily-data rule.
    if (key !== 'workouts' && [current, previous].some(p => p.recorded < 7 || p.fraction < .8)) {
      return {reason: 'sparse'};
    }
    if (summary.previous === 0) return {reason: 'zero-baseline'};
    return {reason: 'available', change: (summary.value - summary.previous) / summary.previous * 100,
      difference: summary.value - summary.previous};
  },
};
