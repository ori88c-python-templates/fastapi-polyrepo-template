"""PUT /api/v1/feature-flags/{name}."""

from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.models.feature_flags import FeatureFlag

_FLAG = FeatureFlag(
    name="dark_mode",
    enabled=False,
    updated_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
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
    )

    assert response.status_code == HTTPStatus.OK
    assert FeatureFlag.model_validate(response.json()) == _FLAG
