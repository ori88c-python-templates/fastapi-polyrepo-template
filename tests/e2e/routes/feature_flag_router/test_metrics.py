"""Product HTTP followed by GET /metrics on the same process."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.config import METRICS_ENDPOINT

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/api/v1/feature-flags/dark_mode"
_FEATURE_FLAG_HANDLER = 'handler="/api/v1/feature-flags/{name}"'


def _unlabeled_counter(body: str, name: str) -> float:
    """Return the value of an unlabeled counter, or 0.0 if the series is absent.

    Args:
        body: Prometheus exposition text from ``GET /metrics``.
        name: Metric name with no labels.

    Returns:
        The scraped value.
    """
    prefix = f"{name} "
    for line in body.splitlines():
        if line.startswith("#") or not line.startswith(prefix):
            continue
        return float(line.split()[-1])
    return 0.0


async def test_put_then_get_increments_feature_flag_and_http_metrics(
    client: AsyncClient,
) -> None:
    """Business counters and default HTTP series share the scrape path."""
    before = (await client.get(METRICS_ENDPOINT)).text

    created = await client.put(_PATH, json={"enabled": True})
    loaded = await client.get(_PATH)
    metrics = await client.get(METRICS_ENDPOINT)

    assert created.status_code == HTTPStatus.OK
    assert loaded.status_code == HTTPStatus.OK
    assert metrics.status_code == HTTPStatus.OK
    body = metrics.text
    assert _unlabeled_counter(body, "feature_flag_writes_total") == (
        _unlabeled_counter(before, "feature_flag_writes_total") + 1.0
    )
    assert _unlabeled_counter(body, "feature_flag_reads_total") == (
        _unlabeled_counter(before, "feature_flag_reads_total") + 1.0
    )
    assert "http_requests_total" in body
    assert _FEATURE_FLAG_HANDLER in body
