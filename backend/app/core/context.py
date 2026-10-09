from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    HR_ADMIN = "HR_ADMIN"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Identity of the caller, built only from a verified JWT and never from model output (PR-1).

    Every service, tool and database session receives this object, so access decisions
    always use the same trusted identity.
    """

    user_id: UUID
    role: Role
    tenant_id: UUID | None
    company_id: UUID | None
    employee_id: UUID | None
    # When the token was issued; used to revoke sessions older than a password change.
    # Not part of identity, so it is excluded from equality.
    issued_at: datetime | None = field(default=None, compare=False)

    @property
    def is_platform_admin(self) -> bool:
        return self.role is Role.PLATFORM_ADMIN
