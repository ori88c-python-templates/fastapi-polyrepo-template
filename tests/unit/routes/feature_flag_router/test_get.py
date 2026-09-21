"""GET /api/v1/feature-flags/{name}."""

from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.models.feature_flags import FeatureFlag
from app.services import FeatureFlagNotFoundError

_FLAG = FeatureFlag(
    name="dark_mode",
    enabled=True,
    updated_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
)


async def test_get_returns_the_flag(
    feature_flag_client: AsyncClient,
    feature_flag_service: AsyncMock,
) -> None:
    """A known flag is returned as JSON with the documented fields."""
    feature_flag_service.get_flag.return_value = _FLAG

    response = await feature_flag_client.get("/api/v1/feature-flags/dark_mode")

    assert response.status_code == HTTPStatus.OK
    assert FeatureFlag.model_validate(response.json()) == _FLAG


async def test_get_returns_not_found_when_the_service_has_no_row(
    feature_flag_client: AsyncClient,
    feature_flag_service: AsyncMock,
) -> None:
    """A missing flag is a 404, not a disabled flag."""
    feature_flag_service.get_flag.side_effect = FeatureFlagNotFoundError("missing")

    response = await feature_flag_client.get("/api/v1/feature-flags/missing")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"detail": "Feature flag 'missing' does not exist."}
