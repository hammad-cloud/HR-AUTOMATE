from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.context import RequestContext, Role
from app.core.exceptions import UnauthenticatedError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(ctx: RequestContext) -> str:
    """Issue a JWT that carries user_id, tenant_id, company_id and role (FR-01)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(ctx.user_id),
        "role": ctx.role.value,
        "tid": str(ctx.tenant_id) if ctx.tenant_id else None,
        "cid": str(ctx.company_id) if ctx.company_id else None,
        "eid": str(ctx.employee_id) if ctx.employee_id else None,
        # Sub-second precision so a password change revokes exactly the tokens issued before it.
        "iat": now.timestamp(),
        "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _uuid_or_none(value: str | None) -> UUID | None:
    return UUID(value) if value else None


def decode_access_token(token: str) -> RequestContext:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        role = Role(payload["role"])
        ctx = RequestContext(
            user_id=UUID(payload["sub"]),
            role=role,
            tenant_id=_uuid_or_none(payload.get("tid")),
            company_id=_uuid_or_none(payload.get("cid")),
            employee_id=_uuid_or_none(payload.get("eid")),
            issued_at=datetime.fromtimestamp(payload["iat"], UTC) if "iat" in payload else None,
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise UnauthenticatedError("Invalid or expired token") from exc

    # Only the platform admin may exist without a tenant.
    if ctx.tenant_id is None and role is not Role.PLATFORM_ADMIN:
        raise UnauthenticatedError("Token is missing tenant context")
    return ctx
