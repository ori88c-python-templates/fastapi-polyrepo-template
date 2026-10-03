"""PUT /api/v1/feature-flags/{name}."""

from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.config import TENANT_ID_HEADER, USER_ID_HEADER
from app.models.feature_flags import FeatureFlag
from app.models.user_details import UserDetails

_CALLER = UserDetails(tenant_id="tenant-a", user_id="user-1")
_HEADERS = {TENANT_ID_HEADER: _CALLER.tenant_id, USER_ID_HEADER: _CALLER.user_id}
_FLAG = FeatureFlag(
    name="dark_mode",
    enabled=False,
    updated_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    updated_by_user_id=_CALLER.user_id,
)


async def test_put_returns_the_stored_flag(
    feature_flag_client: AsyncClient,
    feature_flag_service: AsyncMock,
) -> None:
    """An upsert is returned as JSON with the documented fields."""
    feature_flag_service.set_flag.return_value = _FLAG

    response = await feature_flag_client.put(
        "/api/v1/feature-flags/dark_mode",
        json={"enabled": False},
        headers=_HEADERS,
    )

    assert response.status_code == HTTPStatus.OK
    assert FeatureFlag.model_validate(response.json()) == _FLAG
    feature_flag_service.set_flag.assert_awaited_once_with(
        "dark_mode",
        False,
        _CALLER,
    )
