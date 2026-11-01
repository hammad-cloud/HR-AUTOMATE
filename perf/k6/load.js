// Load test: the expected busy-hour traffic. 50 concurrent users (roughly a 500-employee
// company at peak) with realistic think time, held for 5 minutes. Must meet every SLO.
import { SLO_THRESHOLDS, loginAll } from './lib/config.js';
import { mixedTraffic } from './lib/journeys.js';
import { summaryFor } from './lib/summary.js';

const VUS = Number(__ENV.VUS || 50);

export const options = {
  stages: [
    { duration: '1m', target: VUS }, // ramp up
    { duration: __ENV.HOLD || '5m', target: VUS }, // steady state
    { duration: '30s', target: 0 }, // ramp down
  ],
  thresholds: SLO_THRESHOLDS,
};

export const setup = () => loginAll();
export default (tokens) => mixedTraffic(tokens);
export const handleSummary = summaryFor('load');
