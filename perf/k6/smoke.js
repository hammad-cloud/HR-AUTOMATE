// Smoke test: 1 virtual user, every journey once. Proves the scripts and the system work
// before any heavier test is run.
import { loginAll } from './lib/config.js';
import { employeeJourney, hrJourney, managerJourney } from './lib/journeys.js';
import { summaryFor } from './lib/summary.js';

export const options = {
  vus: 1,
  iterations: 3,
  thresholds: {
    http_req_failed: ['rate==0'],
    checks: ['rate==1'],
  },
};

export const setup = () => loginAll();

export default function (tokens) {
  employeeJourney(tokens.employee);
  managerJourney(tokens.manager);
  hrJourney(tokens.hr);
}

export const handleSummary = summaryFor('smoke');
