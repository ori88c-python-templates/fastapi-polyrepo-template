"""Read ``asyncio_event_loop_lag_seconds`` from a private registry."""

from prometheus_client import CollectorRegistry

METRIC_NAME = "asyncio_event_loop_lag_seconds"


def sample_value(registry: CollectorRegistry, suffix: str, *, le: str | None = None) -> float:
    """Return one histogram sample.

    Args:
        registry: Collector the monitor was constructed with.
        suffix: ``_sum``, ``_count``, or ``_bucket``.
        le: Bucket bound when ``suffix`` is ``_bucket``. Omit for sum and count.

    Returns:
        The sample value.

    Raises:
        AssertionError: If that sample is not in the registry.
    """
    name = f"{METRIC_NAME}{suffix}"
    for collected in registry.collect():
        for sample in collected.samples:
            if sample.name != name:
                continue
            if le is None:
                if sample.labels:
                    continue
                return float(sample.value)
            if sample.labels.get("le") == le:
                return float(sample.value)
    bound = f" le={le}" if le is not None else ""
    raise AssertionError(f"{name}{bound} was not registered")
