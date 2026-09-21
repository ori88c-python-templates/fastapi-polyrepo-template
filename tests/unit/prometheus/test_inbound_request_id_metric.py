"""HTTP-layer dummy series that counts inbound X-Request-ID."""

from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry

from app.config import METRICS_ENDPOINT, REQUEST_ID_HEADER
from tests.unit.prometheus.helpers import instrumented_app

_INBOUND_METRIC: str = "http_requests_with_inbound_request_id_total"


async def test_inbound_request_id_custom_metric_increments() -> None:
    """The HTTP-layer dummy series counts callers that already sent X-Request-ID."""
    app = instrumented_app(CollectorRegistry())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
    ) as client:
        await client.get("/ping", headers={REQUEST_ID_HEADER: "from-test"})
        metrics_response = await client.get(METRICS_ENDPOINT)

    assert f"{_INBOUND_METRIC} 1.0" in metrics_response.text


async def test_inbound_request_id_custom_metric_skips_generated_ids() -> None:
    """A request that did not send X-Request-ID is not counted."""
    app = instrumented_app(CollectorRegistry())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
    ) as client:
        await client.get("/ping")
        metrics_response = await client.get(METRICS_ENDPOINT)

    assert f"{_INBOUND_METRIC} 0.0" in metrics_response.text
