from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.context import Role
from app.schemas.common import APIModel


class LoginRequest(BaseModel):
    # Deliberately not EmailStr: demo tenants use reserved .test domains, and an unknown
    # address simply fails the credential check.
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def _must_differ(self) -> "ChangePasswordRequest":
        if self.new_password == self.current_password:
            raise ValueError("The new password must be different from the current one")
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105  (OAuth2 token type, not a secret)
    expires_in: int


class CurrentUser(APIModel):
    user_id: UUID
    email: str
    role: Role
    tenant_id: UUID | None
    tenant_name: str | None
    company_id: UUID | None
    employee_id: UUID | None
    full_name: str
    job_title: str | None
    department: str | None
