// Soak (endurance) test: normal load held for a long time to expose memory leaks,
// connection-pool exhaustion and slow degradation. Default 30 minutes; use
// SOAK_DURATION=4h for a full endurance run.
import { SLO_THRESHOLDS, loginAll } from './lib/config.js';
import { mixedTraffic } from './lib/journeys.js';
import { summaryFor } from './lib/summary.js';

export const options = {
  stages: [
    { duration: '2m', target: Number(__ENV.VUS || 30) },
    { duration: __ENV.SOAK_DURATION || '30m', target: Number(__ENV.VUS || 30) },
    { duration: '1m', target: 0 },
  ],
  thresholds: SLO_THRESHOLDS,
};

export const setup = () => loginAll();
export default (tokens) => mixedTraffic(tokens);
export const handleSummary = summaryFor('soak');
