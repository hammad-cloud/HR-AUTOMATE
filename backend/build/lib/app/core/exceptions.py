from enum import StrEnum


class ErrorCode(StrEnum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Base class for errors that map to a typed API response."""

    status_code: int = 500
    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnauthenticatedError(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHENTICATED


class PermissionDeniedError(AppError):
    """Raised when the policy layer refuses an action (PR-7). Always audited by the caller."""

    status_code = 403
    code = ErrorCode.PERMISSION_DENIED


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND


class BusinessRuleError(AppError):
    status_code = 422
    code = ErrorCode.BUSINESS_RULE_VIOLATION


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.CONFLICT
