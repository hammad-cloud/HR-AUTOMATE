# ADR 0004: Backend-for-Frontend with an httpOnly session cookie

- **Status:** Accepted
- **Date:** 2026-10-06

## Context

The web app needs the API's JWT. Storing it in `localStorage` exposes it to any XSS, and calling
the API directly from the browser requires CORS and leaks the API surface to clients.

## Decision

Next.js acts as a Backend-for-Frontend. Login runs in a Server Action that stores the JWT in an
`httpOnly`, `SameSite=Lax` (and `Secure` in production) cookie. Server components and Server
Actions call the API through a `server-only` client that attaches the token. Browser JavaScript
never sees it. `proxy.ts` makes only an optimistic redirect; the API authorizes every request.

## Consequences

- No token in browser storage; CSRF is mitigated by SameSite and Server Action origin checks.
- Server Actions are public endpoints, so they carry no authority. They forward the token and the API decides.
- Streaming chat (milestone 3) will go through a Next.js route handler that proxies the API's stream with the same cookie.
