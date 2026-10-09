from fastapi import APIRouter

from app.api.deps import AnonymousSession, Context, Session
from app.core.config import get_settings
from app.schemas.auth import ChangePasswordRequest, CurrentUser, LoginRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AnonymousSession) -> TokenResponse:
    token = await auth_service.authenticate(session, body.email, body.password)
    return TokenResponse(access_token=token, expires_in=get_settings().jwt_ttl_minutes * 60)


@router.get("/me", response_model=CurrentUser)
async def me(ctx: Context, session: Session) -> CurrentUser:
    return await auth_service.get_current_user(session, ctx)


@router.post("/password", response_model=TokenResponse)
async def change_password(
    body: ChangePasswordRequest, ctx: Context, session: Session
) -> TokenResponse:
    """Change your own password. Every other session is signed out; use the returned token."""
    token = await auth_service.change_password(
        session, ctx, body.current_password, body.new_password
    )
    return TokenResponse(access_token=token, expires_in=get_settings().jwt_ttl_minutes * 60)
