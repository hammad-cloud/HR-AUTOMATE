from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.core.security import BCRYPT_MAX_BYTES


def _fits_bcrypt(value: str) -> str:
    if len(value.encode()) > BCRYPT_MAX_BYTES:
        raise ValueError(f"must be at most {BCRYPT_MAX_BYTES} bytes")
    return value


# Every password that will be hashed: 8+ characters and within bcrypt's 72-byte input limit
# (72 ASCII characters, fewer when the password uses multi-byte characters).
NewPassword = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(_fits_bcrypt)]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
