"""PUT /api/v1/feature-flags/{name} through the real application."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.models.feature_flags import FeatureFlag
from tests.e2e.routes.feature_flag_router.helpers import caller_headers

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/api/v1/feature-flags/dark_mode"


async def test_put_creates_a_flag(client: AsyncClient) -> None:
    """A new name is stored and returned as JSON, with the caller as editor."""
    response = await client.put(_PATH, json={"enabled": True}, headers=caller_headers())

    assert response.status_code == HTTPStatus.OK
    flag = FeatureFlag.model_validate(response.json())
    assert flag.name == "dark_mode"
    assert flag.enabled is True
    assert flag.updated_by_user_id == "user-1"


async def test_put_updates_an_existing_flag(client: AsyncClient) -> None:
    """A second write is what GET returns, not the first value."""
    await client.put(
        _PATH,
        json={"enabled": True},
        headers=caller_headers(user_id="user-1"),
    )

    updated = await client.put(
        _PATH,
        json={"enabled": False},
        headers=caller_headers(user_id="user-2"),
    )
    loaded = await client.get(_PATH, headers=caller_headers(user_id="user-2"))

    assert updated.status_code == HTTPStatus.OK
    assert FeatureFlag.model_validate(updated.json()).enabled is False
    assert FeatureFlag.model_validate(updated.json()).updated_by_user_id == "user-2"
    assert FeatureFlag.model_validate(loaded.json()).enabled is False
    assert FeatureFlag.model_validate(loaded.json()).updated_by_user_id == "user-2"
