// Spike test: a sudden surge (e.g. everyone opening payslips on payday). Jumps from 10 to
// 300 users in 10 seconds, holds, then drops back to check the system recovers.
import { loginAll } from './lib/config.js';
import { mixedTraffic } from './lib/journeys.js';
import { summaryFor } from './lib/summary.js';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '10s', target: 300 }, // spike
    { duration: '1m', target: 300 },
    { duration: '10s', target: 10 }, // drop
    { duration: '1m', target: 10 }, // recovery window
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    'http_req_duration{type:read}': ['p(95)<3000'],
  },
};

export const setup = () => loginAll();
export default (tokens) => mixedTraffic(tokens);
export const handleSummary = summaryFor('spike');
