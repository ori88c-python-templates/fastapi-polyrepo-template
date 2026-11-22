"""The lag series is registered only on the registry passed in."""

from prometheus_client import REGISTRY, CollectorRegistry, generate_latest

from app.metrics import EventLoopLagMonitor
from tests.unit.metrics.event_loop_lag_monitor.helpers import METRIC_NAME


def test_series_is_absent_from_the_process_registry() -> None:
    """Constructing the monitor does not touch the process-wide registry."""
    registry = CollectorRegistry()
    EventLoopLagMonitor(registry)

    process_body = generate_latest(REGISTRY).decode()
    private_body = generate_latest(registry).decode()

    assert METRIC_NAME not in process_body
    assert METRIC_NAME in private_body
