from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.schemas.common import APIModel


class AuditEntryMeta(APIModel):
    """Metadata-only view, the most a PLATFORM_ADMIN may see (FR-62)."""

    id: int
    ts: datetime
    tenant_id: UUID | None
    user_id: UUID | None
    channel: str
    event: str
    tool: str | None
    outcome: str
    approval_status: str | None
    model: str | None
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
    cost_usd: Decimal | None


class AuditEntry(AuditEntryMeta):
    conversation_id: UUID | None
    request_id: str | None
    user_message: str | None
    args_redacted: dict[str, Any] | None
    detail: str | None
    # Resolved at read time through RLS, so names only ever come from the reader's own tenant.
    actor_name: str | None = None
    subject_name: str | None = None


class AuditPage(APIModel):
    items: list[AuditEntry] | list[AuditEntryMeta]
    total: int
    limit: int
    offset: int
