"""Business collectors on the scrape registry appear in ``GET /metrics``."""

from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry

from app.config import METRICS_ENDPOINT
from app.metrics import FeatureFlagMetrics
from tests.unit.prometheus.helpers import instrumented_app


async def test_service_collectors_appear_on_the_same_scrape() -> None:
    """Business series must share the instrumentator's registry to be scraped."""
    registry = CollectorRegistry()
    app = instrumented_app(registry)
    collectors = FeatureFlagMetrics(registry=registry)
    collectors.reads_total.inc()
    collectors.writes_total.inc()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
    ) as client:
        metrics_response = await client.get(METRICS_ENDPOINT)

    body = metrics_response.text
    assert "feature_flag_reads_total 1.0" in body
    assert "feature_flag_writes_total 1.0" in body
