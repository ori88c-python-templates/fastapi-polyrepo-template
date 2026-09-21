"""The metrics endpoint serves default HTTP series after a real request."""

from http import HTTPStatus

from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry

from app.config import METRICS_ENDPOINT
from tests.unit.prometheus.helpers import instrumented_app


async def test_metrics_endpoint_records_an_http_request() -> None:
    """Wiring check: after a real request, ``/metrics`` contains default HTTP series."""
    app = instrumented_app(CollectorRegistry())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
    ) as client:
        ping = await client.get("/ping")
        metrics_response = await client.get(METRICS_ENDPOINT)

    assert ping.status_code == HTTPStatus.OK
    assert metrics_response.status_code == HTTPStatus.OK
    body = metrics_response.text
    assert "http_requests_total" in body
    assert 'handler="/ping"' in body


async def test_metrics_endpoint_uses_prometheus_text_plain() -> None:
    """Scrapes are Prometheus exposition format, not JSON."""
    app = instrumented_app(CollectorRegistry())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
    ) as client:
        metrics_response = await client.get(METRICS_ENDPOINT)

    assert "text/plain" in metrics_response.headers["content-type"]
