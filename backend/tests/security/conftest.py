"""Security suite fixtures. Reuses the integration fixtures (running Postgres + seed data)."""

import pytest

from tests.integration.conftest import (  # noqa: F401 - re-exported pytest fixtures
    ayesha,
    client,
    globex_tenant_id,
    omar,
    owner_engine,
    platform_admin,
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/security" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.security)
            item.add_marker(pytest.mark.integration)
