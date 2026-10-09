from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.exceptions import UnauthenticatedError
from app.core.security import decode_access_token
from app.db.session import scoped_session
from app.services import auth_service

_bearer = HTTPBearer(auto_error=False)


async def get_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> RequestContext:
    if credentials is None:
        raise UnauthenticatedError("Missing bearer token")
    ctx = decode_access_token(credentials.credentials)
    # Exposed to the exception handlers so denials are audited against the right identity.
    request.state.ctx = ctx
    return ctx


async def get_session(
    ctx: Annotated[RequestContext, Depends(get_context)],
) -> AsyncIterator[AsyncSession]:
    async with scoped_session(ctx) as session:
        await auth_service.ensure_session_current(session, ctx)
        yield session


async def get_anonymous_session() -> AsyncIterator[AsyncSession]:
    """A session with empty RLS context: every tenant table reads as empty (used by login)."""
    async with scoped_session(None) as session:
        yield session


Context = Annotated[RequestContext, Depends(get_context)]
Session = Annotated[AsyncSession, Depends(get_session)]
AnonymousSession = Annotated[AsyncSession, Depends(get_anonymous_session)]
