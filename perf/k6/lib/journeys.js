// Realistic user journeys, one per role, mirroring what the web app requests per page.
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { API, authHeaders } from './config.js';

function get(token, path, name) {
  const params = authHeaders(token);
  params.tags = { name: `GET ${name}`, type: 'read' };
  const res = http.get(`${API}${path}`, params);
  check(res, { [`${name} 200`]: (r) => r.status === 200 });
  return res;
}

function think() {
  sleep(1 + Math.random() * 2); // 1-3 s between page views
}

export function employeeJourney(token) {
  group('employee: dashboard', () => {
    get(token, '/dashboard', '/dashboard');
    get(token, '/auth/me', '/auth/me');
  });
  think();
  group('employee: leave page', () => {
    get(token, '/leave/balances', '/leave/balances');
    get(token, '/leave/requests?scope=mine', '/leave/requests');
    get(token, '/leave/types', '/leave/types');
  });
  think();
  group('employee: attendance and payslips', () => {
    get(token, '/attendance', '/attendance');
    get(token, '/payslips', '/payslips');
  });
  think();
}

export function managerJourney(token) {
  group('manager: dashboard', () => {
    get(token, '/dashboard', '/dashboard');
  });
  think();
  group('manager: approvals', () => {
    get(token, '/leave/approvals', '/leave/approvals');
    get(token, '/leave/requests?scope=team', '/leave/requests');
  });
  think();
  group('manager: team', () => {
    const team = get(token, '/employees', '/employees');
    const members = team.status === 200 ? team.json() : [];
    if (members.length) {
      const member = members[Math.floor(Math.random() * members.length)];
      get(token, `/employees/${member.id}`, '/employees/{id}');
      get(token, `/attendance?employee_id=${member.id}`, '/attendance');
    }
  });
  think();
}

const SEARCHES = ['a', 'Khan', 'Eng', 'Ali', 'Sales', 'Raza'];

export function hrJourney(token) {
  group('hr: dashboard', () => {
    get(token, '/dashboard', '/dashboard');
  });
  think();
  group('hr: team directory', () => {
    const term = SEARCHES[Math.floor(Math.random() * SEARCHES.length)];
    get(token, `/employees?search=${term}`, '/employees?search');
    get(token, '/employees', '/employees');
    get(token, '/leave/requests?scope=company', '/leave/requests');
  });
  think();
  group('hr: audit log', () => {
    get(token, '/audit?limit=50', '/audit');
  });
  think();
}

// Traffic mix observed for an HRMS: mostly employees, a few managers and HR admins.
export function mixedTraffic(tokens) {
  const roll = Math.random();
  if (roll < 0.7) employeeJourney(tokens.employee);
  else if (roll < 0.9) managerJourney(tokens.manager);
  else hrJourney(tokens.hr);
}
