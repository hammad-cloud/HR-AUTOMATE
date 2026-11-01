// Shared configuration for every k6 scenario.
import http from 'k6/http';
import { check, fail } from 'k6';

export const BASE_URL = __ENV.BASE_URL || 'http://backend:8000';
export const API = `${BASE_URL}/api/v1`;

const PASSWORD = __ENV.DEMO_PASSWORD;

// Seeded demo personas (see backend/app/seed/seed.py): one per role.
export const PERSONAS = {
  employee: 'ayesha@acme.test',
  manager: 'bilal@acme.test',
  hr: 'sara@acme.test',
};

// Service level objectives the API is held to under normal load.
// p95 < 500 ms and p99 < 1 s for reads, < 1% errors.
export const SLO_THRESHOLDS = {
  http_req_failed: ['rate<0.01'],
  'http_req_duration{type:read}': ['p(95)<500', 'p(99)<1000'],
  'http_req_duration{type:write}': ['p(95)<800'],
  checks: ['rate>0.99'],
};

export function login(email) {
  if (!PASSWORD) fail('Set DEMO_PASSWORD (same value as in .env)');
  const res = http.post(`${API}/auth/login`, JSON.stringify({ email, password: PASSWORD }), {
    headers: { 'Content-Type': 'application/json' },
    tags: { name: 'POST /auth/login', type: 'auth' },
  });
  if (!check(res, { 'login 200': (r) => r.status === 200 })) {
    fail(`login failed for ${email}: ${res.status} ${res.body}`);
  }
  return res.json('access_token');
}

// Log every persona in once; virtual users share the tokens (sign-in is bcrypt-bound
// and is measured separately in the login scenario of performance.js).
export function loginAll() {
  const tokens = {};
  for (const [role, email] of Object.entries(PERSONAS)) tokens[role] = login(email);
  return tokens;
}

export function authHeaders(token) {
  return { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } };
}
