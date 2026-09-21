"""Shared fixtures for the route child-logger tests."""

from collections.abc import AsyncGenerator
from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes import feature_flag_router
from app.services import FeatureFlagService
from app.state import APP_STATE_ATTRIBUTE
from tests.unit.app_state_factory import AppStateFactory


@pytest.fixture
def feature_flag_service() -> AsyncMock:
    """A mock FeatureFlagService with canned responses set by each test.

    Returns:
        An ``AsyncMock`` specced on the real service so awaited methods exist.
    """
    return AsyncMock(spec=FeatureFlagService)


@pytest.fixture
def app(
    make_app_state: AppStateFactory,
    feature_flag_service: AsyncMock,
) -> FastAPI:
    """Mount the feature-flag router on an app whose logs are inspectable.

    Args:
        make_app_state: Shared factory that fills AppState with injected doubles.
        feature_flag_service: The mock the handlers will ``Depends`` on.

    Returns:
        An application with ``AppState`` attached.
    """
    application = FastAPI()
    setattr(
        application.state,
        APP_STATE_ATTRIBUTE,
        make_app_state(feature_flag=cast(FeatureFlagService, feature_flag_service)),
    )
    application.include_router(feature_flag_router)
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Provide a client that speaks ASGI directly to ``app``.

    Args:
        app: The application to send requests to.

    Yields:
        A client bound to that application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://route-logger.test",
    ) as http_client:
        yield http_client
