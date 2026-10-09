"""Integration fixtures. Requires `docker compose up db` plus migrations and seed data."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.context import RequestContext, Role
from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def owner_engine():
    engine = create_engine(get_settings().migration_database_url)
    yield engine
    engine.dispose()


def _persona(owner_engine, email: str) -> RequestContext:
    with owner_engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, role, tenant_id, company_id, employee_id FROM users WHERE email=:e"),
            {"e": email},
        ).one()
    return RequestContext(
        user_id=row.id,
        role=Role(row.role),
        tenant_id=row.tenant_id,
        company_id=row.company_id,
        employee_id=row.employee_id,
    )


@pytest.fixture(scope="session")
def ayesha(owner_engine) -> RequestContext:
    return _persona(owner_engine, "ayesha@acme.test")


@pytest.fixture(scope="session")
def omar(owner_engine) -> RequestContext:
    return _persona(owner_engine, "omar@globex.test")


@pytest.fixture(scope="session")
def platform_admin(owner_engine) -> RequestContext:
    return _persona(owner_engine, "admin@platform.test")


@pytest.fixture(scope="session")
def globex_tenant_id(omar) -> UUID:
    assert omar.tenant_id is not None
    return omar.tenant_id


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def login(client: AsyncClient, email: str, password: str | None = None) -> dict[str, str]:
    password = password or get_settings().demo_password
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


NEW_HIRE_PASSWORD = "Welcome@2026"


def new_hire(**overrides) -> dict:
    """A valid onboarding payload with a unique email (Acme)."""
    body = {
        "full_name": "Test Hire",
        "email": f"hire.{uuid4().hex[:10]}@acme.test",
        "department": "Engineering",
        "job_title": "Software Engineer",
        "join_date": str(date.today()),
        "salary": "200000",
        "national_id": "35202-1234567-1",
        "role": "EMPLOYEE",
        "password": NEW_HIRE_PASSWORD,
    }
    return body | overrides


async def onboard(client: AsyncClient, hr: dict[str, str], **overrides) -> dict:
    r = await client.post("/api/v1/employees", json=new_hire(**overrides), headers=hr)
    assert r.status_code == 201, r.text
    return r.json()
