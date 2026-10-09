import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.exceptions import AppError, ErrorCode, PermissionDeniedError
from app.core.logging import configure_logging, request_id_var
from app.db.session import engine
from app.services import audit_service

logger = logging.getLogger("hr_copilot")


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": request_id_var.get()}},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Permission-aware AI assistant for a multi-tenant HRMS.",
        docs_url="/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            response.headers["x-request-id"] = request_id
            logger.info(
                "%s %s -> %s in %sms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            return response
        finally:
            request_id_var.reset(token)

    @app.exception_handler(PermissionDeniedError)
    async def handle_denied(request: Request, exc: PermissionDeniedError) -> JSONResponse:
        # Every denial is audited centrally, so no individual endpoint can forget (PR-7).
        ctx: RequestContext | None = getattr(request.state, "ctx", None)
        if ctx is not None:
            route = request.scope.get("route")
            template = getattr(route, "path", request.url.path)
            args = {**request.path_params, **request.query_params}
            try:
                await audit_service.record_denial(
                    ctx,
                    event=f"{request.method} {template}"[:60],
                    args=args or None,
                    detail=exc.message,
                )
            except Exception:
                logger.exception("Failed to audit permission denial")
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:])
        message = f"{field}: {first.get('msg', 'Invalid request')}" if field else "Invalid request"
        return _error(422, ErrorCode.VALIDATION_ERROR, message)

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces to clients (NFR-08); the request id links to the server log.
        logger.exception("Unhandled error", exc_info=exc)
        return _error(500, ErrorCode.INTERNAL_ERROR, "Something went wrong. Please try again.")

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["ops"])
    async def ready() -> dict[str, str]:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}

    app.include_router(api_router)
    return app


app = create_app()
