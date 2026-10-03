"""GET /api/v1/feature-flags/{name} through the real application."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.models.feature_flags import FeatureFlag
from tests.e2e.routes.feature_flag_router.helpers import caller_headers

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/api/v1/feature-flags/dark_mode"


async def test_get_returns_not_found_when_the_flag_does_not_exist(
    client: AsyncClient,
) -> None:
    """A missing flag is a 404, not a disabled flag."""
    response = await client.get("/api/v1/feature-flags/missing", headers=caller_headers())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Feature flag 'missing' does not exist."}


async def test_get_returns_a_flag_after_put(client: AsyncClient) -> None:
    """A write is visible to the next read through HTTP."""
    written = await client.put(_PATH, json={"enabled": True}, headers=caller_headers())

    loaded = await client.get(_PATH, headers=caller_headers())

    assert loaded.status_code == HTTPStatus.OK
    flag = FeatureFlag.model_validate(loaded.json())
    assert flag.name == "dark_mode"
    assert flag.enabled is True
    assert flag.updated_by_user_id == "user-1"
    assert flag.updated_at == FeatureFlag.model_validate(written.json()).updated_at


async def test_get_for_another_tenant_is_not_found(client: AsyncClient) -> None:
    """Tenant B does not see the flag tenant A stored under the same name."""
    created = await client.put(
        _PATH,
        json={"enabled": True},
        headers=caller_headers(tenant_id="tenant-a", user_id="user-1"),
    )
    other = await client.get(
        _PATH,
        headers=caller_headers(tenant_id="tenant-b", user_id="user-2"),
    )

    assert created.status_code == HTTPStatus.OK
    assert other.status_code == HTTPStatus.NOT_FOUND
    assert other.json() == {"detail": "Feature flag 'dark_mode' does not exist."}
