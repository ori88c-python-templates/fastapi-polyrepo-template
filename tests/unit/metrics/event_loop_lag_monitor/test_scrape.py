"""The lag histogram is served from the same registry as the HTTP series."""

from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry

from app.config import METRICS_ENDPOINT
from app.metrics import EventLoopLagMonitor
from tests.unit.metrics.event_loop_lag_monitor.helpers import METRIC_NAME
from tests.unit.prometheus.helpers import instrumented_app


async def test_series_appears_on_the_scrape() -> None:
    """``GET /metrics`` includes the histogram registered on the instrumentator registry."""
    registry = CollectorRegistry()
    app = instrumented_app(registry)
    EventLoopLagMonitor(registry)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://metrics.test",
    ) as client:
        metrics_response = await client.get(METRICS_ENDPOINT)

    assert METRIC_NAME in metrics_response.text
