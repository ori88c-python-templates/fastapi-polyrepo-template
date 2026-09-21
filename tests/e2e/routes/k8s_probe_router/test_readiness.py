"""Readiness against real Redis and PostgreSQL."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.config import LIVEZ_ENDPOINT, READYZ_ENDPOINT

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_readiness_returns_ok_when_the_stores_answer(client: AsyncClient) -> None:
    """Real PING and SELECT 1 succeed, so the instance reports itself ready."""
    response = await client.get(READYZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


async def test_readiness_is_a_distinct_path_from_liveness(client: AsyncClient) -> None:
    """Both probes answer on the running app, on their own paths."""
    liveness = await client.get(LIVEZ_ENDPOINT)
    readiness = await client.get(READYZ_ENDPOINT)

    assert liveness.status_code == HTTPStatus.OK
    assert readiness.status_code == HTTPStatus.OK
    assert LIVEZ_ENDPOINT != READYZ_ENDPOINT
