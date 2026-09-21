"""``GET /metrics`` is served but never appears in OpenAPI."""

from http import HTTPStatus

from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry

from app.config import METRICS_ENDPOINT
from tests.unit.prometheus.helpers import instrumented_app


async def test_metrics_is_omitted_from_schema_and_still_served() -> None:
    """Prometheus text is a scrape contract, not product API in Swagger."""
    app = instrumented_app(CollectorRegistry())
    paths = app.openapi().get("paths", {})

    assert METRICS_ENDPOINT not in paths
    assert "/ping" in paths

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
    ) as client:
        response = await client.get(METRICS_ENDPOINT)

    assert response.status_code == HTTPStatus.OK
