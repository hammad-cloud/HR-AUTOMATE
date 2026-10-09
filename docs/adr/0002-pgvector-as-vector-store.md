# ADR 0002: pgvector as the vector store

- **Status:** Accepted
- **Date:** 2026-10-06

## Context

RAG answers must only retrieve documents the caller may see: global product docs, own-tenant
policies, and HR-only documents for HR admins (PR-4).

## Options

| Option | Pros | Cons |
|---|---|---|
| Pinecone / Qdrant | Purpose-built, scales well | Extra infrastructure; tenant filtering is metadata we must remember to apply |
| **pgvector (HNSW)** | Same database and transaction; **RLS applies to vector search** | Less scalable at very large corpus sizes |

## Decision

pgvector with an HNSW index (`vector_cosine_ops`). `doc_chunks` denormalises `tenant_id` and
`visibility` so the RLS `visibility_filter` policy restricts similarity search in the same query.

## Consequences

- Retrieval leakage is prevented by the same mechanism as every other table.
- Corpus size for this product (tens of documents per tenant) is far within pgvector's comfort zone.
- Embedding dimension (1536) is configurable; changing models requires re-embedding.
