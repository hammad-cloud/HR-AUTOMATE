// Writes a console summary plus a JSON file per run into perf/results/.
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

export function summaryFor(name) {
  return (data) => ({
    stdout: textSummary(data, { indent: '  ', enableColors: false }),
    [`/perf/results/${name}-summary.json`]: JSON.stringify(data, null, 2),
  });
}
