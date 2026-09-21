"""PUT /api/v1/feature-flags/{name} through the real application."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.models.feature_flags import FeatureFlag

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/api/v1/feature-flags/dark_mode"


async def test_put_creates_a_flag(client: AsyncClient) -> None:
    """A new name is stored and returned as JSON."""
    response = await client.put(_PATH, json={"enabled": True})

    assert response.status_code == HTTPStatus.OK
    flag = FeatureFlag.model_validate(response.json())
    assert flag.name == "dark_mode"
    assert flag.enabled is True


async def test_put_updates_an_existing_flag(client: AsyncClient) -> None:
    """A second write is what GET returns, not the first value."""
    await client.put(_PATH, json={"enabled": True})

    updated = await client.put(_PATH, json={"enabled": False})
    loaded = await client.get(_PATH)

    assert updated.status_code == HTTPStatus.OK
    assert FeatureFlag.model_validate(updated.json()).enabled is False
    assert FeatureFlag.model_validate(loaded.json()).enabled is False
