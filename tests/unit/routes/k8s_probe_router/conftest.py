"""Shared fixtures for the Kubernetes probe router tests."""

from collections.abc import AsyncGenerator
from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.clients import PostgresClient, RedisClient
from app.routes.k8s_probe_router import k8s_probe_router
from app.state import APP_STATE_ATTRIBUTE
from tests.unit.app_state_factory import AppStateFactory


def _probe_app_with_clients(
    make_app_state: AppStateFactory,
    *,
    redis_fail: bool = False,
    postgres_fail: bool = False,
    include_in_schema: bool = True,
) -> FastAPI:
    """Mount the probe router on an app whose client pings behave as requested.

    Args:
        make_app_state: Shared factory that fills AppState with injected doubles.
        redis_fail: When true, ``RedisClient.ping`` raises ``ConnectionError``.
        postgres_fail: When true, ``PostgresClient.ping`` raises ``ConnectionError``.
        include_in_schema: Whether probe paths appear in OpenAPI. Staging and
            production mount with this false.

    Returns:
        An application with ``AppState`` attached so ``/readyz`` can reach clients.
    """
    redis = AsyncMock(spec=RedisClient)
    if redis_fail:
        redis.ping.side_effect = ConnectionError("redis down")
    postgres = AsyncMock(spec=PostgresClient)
    if postgres_fail:
        postgres.ping.side_effect = ConnectionError("postgres down")

    app = FastAPI()
    setattr(
        app.state,
        APP_STATE_ATTRIBUTE,
        make_app_state(
            redis=cast(RedisClient, redis),
            postgres=cast(PostgresClient, postgres),
        ),
    )
    app.include_router(k8s_probe_router, include_in_schema=include_in_schema)
    return app


@pytest.fixture
def probe_app() -> FastAPI:
    """Build an application carrying the probe router and nothing else.

    Deliberately not the real application. Mounting the router on a bare app means no
    configuration, no state and no clients exist, so any test that passes has proved
    liveness depends on none of them.

    Returns:
        An application exposing only the probe endpoints.
    """
    app = FastAPI()
    app.include_router(k8s_probe_router)

    return app


@pytest.fixture
async def probe_client(probe_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Provide a client that speaks ASGI directly to ``probe_app``.

    Requests go through the real routing, validation and serialisation stack, but over
    an in-process transport rather than a socket. ``ASGITransport`` does not run the
    lifespan, which is the point: liveness is exercised against an application that
    was never started.

    Args:
        probe_app: The application to send requests to.

    Yields:
        A client bound to that application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=probe_app),
        base_url="http://probes.test",
    ) as client:
        yield client


@pytest.fixture
def ready_app(make_app_state: AppStateFactory) -> FastAPI:
    """Build a probe app whose Redis and PostgreSQL pings succeed.

    Args:
        make_app_state: Shared factory that fills AppState with injected doubles.

    Returns:
        An application with healthy mocked clients on ``AppState``.
    """
    return _probe_app_with_clients(make_app_state)


@pytest.fixture
def schema_hidden_probe_app(make_app_state: AppStateFactory) -> FastAPI:
    """Mount probes with OpenAPI inclusion off, as staging and production do.

    Args:
        make_app_state: Shared factory that fills AppState with injected doubles.

    Returns:
        An application whose probe paths are served but omitted from the schema.
    """
    return _probe_app_with_clients(make_app_state, include_in_schema=False)


@pytest.fixture
async def ready_client(ready_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Provide a client that speaks ASGI directly to ``ready_app``.

    Args:
        ready_app: The application to send requests to.

    Yields:
        A client bound to that application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=ready_app),
        base_url="http://probes.test",
    ) as client:
        yield client


@pytest.fixture
def redis_down_app(make_app_state: AppStateFactory) -> FastAPI:
    """Build a probe app whose Redis ping fails.

    Args:
        make_app_state: Shared factory that fills AppState with injected doubles.

    Returns:
        An application whose readiness check cannot succeed.
    """
    return _probe_app_with_clients(make_app_state, redis_fail=True)


@pytest.fixture
async def redis_down_client(redis_down_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Provide a client bound to ``redis_down_app``.

    Args:
        redis_down_app: The application to send requests to.

    Yields:
        A client bound to that application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=redis_down_app),
        base_url="http://probes.test",
    ) as client:
        yield client


@pytest.fixture
def postgres_down_app(make_app_state: AppStateFactory) -> FastAPI:
    """Build a probe app whose PostgreSQL ping fails.

    Args:
        make_app_state: Shared factory that fills AppState with injected doubles.

    Returns:
        An application whose readiness check cannot succeed.
    """
    return _probe_app_with_clients(make_app_state, postgres_fail=True)


@pytest.fixture
async def postgres_down_client(postgres_down_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Provide a client bound to ``postgres_down_app``.

    Args:
        postgres_down_app: The application to send requests to.

    Yields:
        A client bound to that application.
    """
    async with AsyncClient(
        transport=ASGITransport(app=postgres_down_app),
        base_url="http://probes.test",
    ) as client:
        yield client
