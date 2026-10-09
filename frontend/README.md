# HR Copilot Web

Next.js 16 (App Router) + Tailwind v4 + shadcn/ui. See the [root README](../README.md).

```
src/
  app/
    (app)/          authenticated routes: dashboard, profile, leave, approvals,
                    attendance, payslips, team, admin/audit
    login/          sign-in with demo personas
    logout/         clears a stale session cookie
  components/
    layout/         sidebar, mobile nav, user menu
    leave/          apply dialog, approval actions, tables
    shared/         page header, stat card, status badge, pickers
    ui/             shadcn/ui primitives
  lib/
    api/            server-only API client + response types
    actions/        Server Actions (auth, leave). They forward the session and the API authorizes
    auth/           session helpers (requireUser / requireRole)
    navigation.ts   stable route registry, also the future assistant navigate_to allow-list
  proxy.ts          optimistic auth redirect (Next 16's replacement for middleware)
```

```bash
npm install
npm run dev          # http://localhost:3000, expects the API at API_BASE_URL (default :8000)
npx eslint src
npm run build
```
