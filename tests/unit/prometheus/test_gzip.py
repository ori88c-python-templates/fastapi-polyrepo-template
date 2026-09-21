"""Gzip of ``GET /metrics`` follows ``PrometheusConfig.SHOULD_GZIP``."""

import gzip

from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry

from app.config import METRICS_ENDPOINT, PrometheusConfig
from tests.unit.prometheus.helpers import instrumented_app

_GZIP_MAGIC: bytes = b"\x1f\x8b"


def _scrape_text(content: bytes) -> str:
    """Decode scrape bytes, undoing gzip only when the payload is still compressed.

    httpx may already have decompressed the body. Tests must not assume either.

    Args:
        content: Raw ``response.content`` after the client may have decoded it.

    Returns:
        Prometheus exposition text.
    """
    if content.startswith(_GZIP_MAGIC):
        content = gzip.decompress(content)
    return content.decode()


async def test_default_config_does_not_gzip_when_the_client_asks() -> None:
    """``SHOULD_GZIP`` defaults off: CPU over extra bandwidth, even if asked."""
    app = instrumented_app(CollectorRegistry())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
        headers={"Accept-Encoding": "gzip"},
    ) as client:
        await client.get("/ping")
        metrics_response = await client.get(METRICS_ENDPOINT)

    assert metrics_response.headers.get("content-encoding") != "gzip"
    assert not metrics_response.content.startswith(_GZIP_MAGIC)
    assert "http_requests_total" in _scrape_text(metrics_response.content)


async def test_gzip_compresses_when_enabled_and_the_client_asks() -> None:
    """Enabled gzip is a Content-Encoding contract Prometheus scrapers honour."""
    app = instrumented_app(
        CollectorRegistry(),
        PrometheusConfig(SHOULD_GZIP=True),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
        headers={"Accept-Encoding": "gzip"},
    ) as client:
        await client.get("/ping")
        metrics_response = await client.get(METRICS_ENDPOINT)

    assert metrics_response.headers.get("content-encoding") == "gzip"
    assert "http_requests_total" in _scrape_text(metrics_response.content)
