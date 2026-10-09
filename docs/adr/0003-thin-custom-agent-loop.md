# ADR 0003: Thin custom agent loop over an agent framework

- **Status:** Accepted (implementation in milestone 3)
- **Date:** 2026-10-06

## Context

The assistant must call tools under strict permission hooks, cap steps (≤ 8 per turn), turn write
tools into confirmation proposals, and audit every step with tokens, latency and cost.

## Options

1. **LangGraph / LlamaIndex agents.** Rich features, but permission and audit hooks sit inside framework abstractions.
2. **Thin custom loop** on the provider SDK's native tool calling.

## Decision

A thin custom loop. Tools are Pydantic-typed functions that call the existing `services/*` layer
with the caller's `RequestContext`; the executor validates arguments, enforces the role-filtered
tool allow-list and converts write tools into `action_proposals`.

## Consequences

- Every security decision is in readable code we own, which also makes it easy to explain in review.
- We implement retries, streaming and step limits ourselves (small, well-understood code).
- Swapping LLM providers stays possible behind a small client interface.
