"""GET /api/v1/feature-flags/{name} through the real application."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.models.feature_flags import FeatureFlag

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/api/v1/feature-flags/dark_mode"


async def test_get_returns_not_found_when_the_flag_does_not_exist(
    client: AsyncClient,
) -> None:
    """A missing flag is a 404, not a disabled flag."""
    response = await client.get("/api/v1/feature-flags/missing")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Feature flag 'missing' does not exist."}


async def test_get_returns_a_flag_after_put(client: AsyncClient) -> None:
    """A write is visible to the next read through HTTP."""
    written = await client.put(_PATH, json={"enabled": True})

    loaded = await client.get(_PATH)

    assert loaded.status_code == HTTPStatus.OK
    flag = FeatureFlag.model_validate(loaded.json())
    assert flag.name == "dark_mode"
    assert flag.enabled is True
    assert flag.updated_at == FeatureFlag.model_validate(written.json()).updated_at
