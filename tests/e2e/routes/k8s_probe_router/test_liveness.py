"""Liveness against the real application: the process can serve."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.config import LIVEZ_ENDPOINT

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    """A running process reports itself alive over HTTP."""
    response = await client.get(LIVEZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}
