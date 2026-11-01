// Stress test: step the load well past normal (50 -> 400 users) to find where latency
// degrades and where errors start. Thresholds only abort on collapse, so the run reports
// the breaking point instead of stopping at the first SLO miss.
import { loginAll } from './lib/config.js';
import { mixedTraffic } from './lib/journeys.js';
import { summaryFor } from './lib/summary.js';

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '2m', target: 50 },
    { duration: '1m', target: 100 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 200 },
    { duration: '2m', target: 200 },
    { duration: '1m', target: 400 },
    { duration: '2m', target: 400 },
    { duration: '1m', target: 0 }, // recovery
  ],
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '30s' }],
    'http_req_duration{type:read}': ['p(95)<2000'],
  },
};

export const setup = () => loginAll();
export default (tokens) => mixedTraffic(tokens);
export const handleSummary = summaryFor('stress');
