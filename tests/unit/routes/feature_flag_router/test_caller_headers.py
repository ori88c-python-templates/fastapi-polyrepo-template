"""GET and PUT require both caller headers before the service runs."""

from http import HTTPStatus
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.config import TENANT_ID_HEADER, USER_ID_HEADER

_PATH = "/api/v1/feature-flags/dark_mode"


async def test_get_without_a_tenant_header_is_unprocessable(
    feature_flag_client: AsyncClient,
    feature_flag_service: AsyncMock,
) -> None:
    """A missing tenant header is 422 and does not call the service."""
    response = await feature_flag_client.get(
        _PATH,
        headers={USER_ID_HEADER: "user-1"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    feature_flag_service.get_flag.assert_not_called()


async def test_get_without_a_user_header_is_unprocessable(
    feature_flag_client: AsyncClient,
    feature_flag_service: AsyncMock,
) -> None:
    """A missing user header is 422 and does not call the service."""
    response = await feature_flag_client.get(
        _PATH,
        headers={TENANT_ID_HEADER: "tenant-a"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    feature_flag_service.get_flag.assert_not_called()


async def test_get_with_a_blank_tenant_header_is_unprocessable(
    feature_flag_client: AsyncClient,
    feature_flag_service: AsyncMock,
) -> None:
    """A blank tenant header is 422 and does not call the service."""
    response = await feature_flag_client.get(
        _PATH,
        headers={TENANT_ID_HEADER: "  ", USER_ID_HEADER: "user-1"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    feature_flag_service.get_flag.assert_not_called()


async def test_put_without_caller_headers_is_unprocessable(
    feature_flag_client: AsyncClient,
    feature_flag_service: AsyncMock,
) -> None:
    """PUT without either header is 422 and does not call the service."""
    response = await feature_flag_client.put(_PATH, json={"enabled": True})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    feature_flag_service.set_flag.assert_not_called()
