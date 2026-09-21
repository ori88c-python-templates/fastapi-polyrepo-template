"""Shared fixtures for the correlation-id middleware tests."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.logger import LogManager
from tests.unit.middlewares.correlation_id_middleware.helpers import build_logging_app


@pytest.fixture
def app(log_manager: LogManager) -> FastAPI:
    """Build the tiny logging app wrapped in ``CorrelationIdMiddleware``.

    Args:
        log_manager: Manager the ``/ping`` handler logs through.

    Returns:
        An application exposing ``GET /ping``.
    """
    return build_logging_app(log_manager)


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Provide a client that speaks ASGI directly to the tiny app.

    Args:
        app: The application to send requests to.

    Yields:
        A client bound to that application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://correlation.test",
    ) as http_client:
        yield http_client
