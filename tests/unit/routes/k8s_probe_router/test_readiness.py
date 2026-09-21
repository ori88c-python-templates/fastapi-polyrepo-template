"""The readiness probe: dependency checks, and what a failure looks like."""

from http import HTTPStatus

from httpx import AsyncClient

from app.config import LIVEZ_ENDPOINT, READYZ_ENDPOINT


async def test_readiness_returns_ok(ready_client: AsyncClient) -> None:
    """When Redis and PostgreSQL both ping, the instance reports itself ready."""
    response = await ready_client.get(READYZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK


async def test_readiness_body_reports_ok(ready_client: AsyncClient) -> None:
    """The body matches the documented schema exactly, with no extra keys."""
    response = await ready_client.get(READYZ_ENDPOINT)

    assert response.json() == {"status": "ok"}


async def test_readiness_is_reported_separately_from_liveness(
    ready_client: AsyncClient,
) -> None:
    """The two probes are distinct endpoints, not one aliased to the other.

    They diverge as soon as a client exists: readiness will check dependencies and start
    failing, while liveness must keep succeeding. Keeping them separate paths is what
    lets Kubernetes drain traffic from a pod without also restarting it.
    """
    liveness = await ready_client.get(LIVEZ_ENDPOINT)
    readiness = await ready_client.get(READYZ_ENDPOINT)

    assert liveness.status_code == HTTPStatus.OK
    assert readiness.status_code == HTTPStatus.OK


async def test_readiness_fails_when_redis_is_down(redis_down_client: AsyncClient) -> None:
    """A Redis ping failure removes the pod from service without killing it."""
    response = await redis_down_client.get(READYZ_ENDPOINT)

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Redis failed a health check."}


async def test_readiness_fails_when_postgres_is_down(
    postgres_down_client: AsyncClient,
) -> None:
    """A PostgreSQL ping failure removes the pod from service without killing it."""
    response = await postgres_down_client.get(READYZ_ENDPOINT)

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "PostgreSQL failed a health check."}
