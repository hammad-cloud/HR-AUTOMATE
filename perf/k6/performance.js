// Performance baseline: fixed request rate per endpoint, so latency is measured without
// queueing effects. Produces the per-endpoint numbers in docs/testing/PERFORMANCE-REPORT.md.
import http from 'k6/http';
import { check } from 'k6';
import { API, PERSONAS, authHeaders, login, loginAll } from './lib/config.js';
import { summaryFor } from './lib/summary.js';

const ENDPOINTS = [
  ['employee', '/dashboard'],
  ['employee', '/auth/me'],
  ['employee', '/leave/balances'],
  ['employee', '/leave/requests?scope=mine'],
  ['employee', '/attendance'],
  ['employee', '/payslips'],
  ['manager', '/leave/approvals'],
  ['hr', '/employees'],
  ['hr', '/employees?search=Khan'],
  ['hr', '/leave/requests?scope=company'],
  ['hr', '/audit?limit=50'],
];

const RATE = Number(__ENV.RATE || 10); // requests per second, per endpoint
const DURATION = __ENV.DURATION || '1m';

const scenarios = {
  // Sign-in is deliberately slow (bcrypt cost 12), so it is measured on its own at 2 rps.
  login: {
    executor: 'constant-arrival-rate',
    exec: 'signIn',
    rate: 2,
    timeUnit: '1s',
    duration: DURATION,
    preAllocatedVUs: 10,
  },
};
const thresholds = {
  http_req_failed: ['rate<0.01'],
  'http_req_duration{name:POST /auth/login}': ['p(95)<1500'],
};

ENDPOINTS.forEach(([role, path], i) => {
  const name = `GET ${path.split('?')[0]}${path.includes('search') ? '?search' : ''}`;
  scenarios[`ep${i}`] = {
    executor: 'constant-arrival-rate',
    exec: 'endpoint',
    env: { ROLE: role, PATH: path, NAME: name },
    rate: RATE,
    timeUnit: '1s',
    duration: DURATION,
    preAllocatedVUs: 5,
    maxVUs: 50,
  };
  thresholds[`http_req_duration{name:${name}}`] = ['p(95)<300'];
});

export const options = { scenarios, thresholds, summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'] };

export const setup = () => loginAll();

export function endpoint(tokens) {
  const params = authHeaders(tokens[__ENV.ROLE]);
  params.tags = { name: __ENV.NAME, type: 'read' };
  const res = http.get(`${API}${__ENV.PATH}`, params);
  check(res, { 'status 200': (r) => r.status === 200 });
}

export function signIn() {
  login(PERSONAS.employee);
}

export const handleSummary = summaryFor('performance');
