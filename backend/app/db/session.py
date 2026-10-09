from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.context import RequestContext

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True, pool_size=10)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

_SET_RLS_CONTEXT = text(
    "SELECT set_config('app.tenant_id', :tenant_id, true),"
    "       set_config('app.user_id', :user_id, true),"
    "       set_config('app.role', :role, true)"
)


async def apply_rls_context(session: AsyncSession, ctx: RequestContext | None) -> None:
    """Bind the verified caller identity to the current transaction (equivalent to SET LOCAL).

    The values come exclusively from the decoded JWT. Because they are transaction-local they
    can never leak to the next request that reuses this pooled connection. With no context the
    settings are empty, and every RLS policy evaluates to "no rows" (fail closed).
    """
    await session.execute(
        _SET_RLS_CONTEXT,
        {
            "tenant_id": str(ctx.tenant_id) if ctx and ctx.tenant_id else "",
            "user_id": str(ctx.user_id) if ctx else "",
            "role": ctx.role.value if ctx else "",
        },
    )


@asynccontextmanager
async def scoped_session(ctx: RequestContext | None) -> AsyncIterator[AsyncSession]:
    """One transaction per unit of work, with RLS context applied before any query runs."""
    async with SessionFactory() as session:
        await apply_rls_context(session, ctx)
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
