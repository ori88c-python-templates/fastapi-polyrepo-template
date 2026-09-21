"""Shared fixtures for the unhandled HTTP exception handler tests."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.logger import LogManager
from tests.unit.middlewares.unhandled_http_exception_handler.helpers import (
    build_unhandled_exception_app,
)


@pytest.fixture
def app(log_manager: LogManager) -> FastAPI:
    """Build the tiny app wrapped like production's exception path.

    Args:
        log_manager: Manager the ``uvicorn`` handler logs through.

    Returns:
        An application exposing ``GET /boom``, ``GET /missing``, and ``GET /ok``.
    """
    return build_unhandled_exception_app(log_manager)


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Provide a client that does not re-raise app exceptions.

    Args:
        app: The application to send requests to.

    Yields:
        A client bound to that application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://unhandled.test",
    ) as http_client:
        yield http_client
