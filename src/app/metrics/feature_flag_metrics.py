"""Prometheus collectors for feature-flag operations."""

from typing import Final

from prometheus_client import CollectorRegistry, Counter


class FeatureFlagMetrics:
    """Counters for feature-flag reads and writes, bound to one Prometheus registry.

    Constructed by the composition root and injected into
    ``FeatureFlagService``. The registry must be the same one
    ``PrometheusManager`` exposes at ``/metrics``, or scrapes will not see
    these series.

    Attributes:
        reads_total: Incremented once per ``get_flag`` call, including misses.
        writes_total: Incremented once per ``set_flag`` that persisted a flag.
    """

    def __init__(self, registry: CollectorRegistry) -> None:
        """Register the dummy read and write counters.

        Args:
            registry: Collector to register with. Must be the same registry
                ``PrometheusManager`` scrapes in production. Tests pass a
                private registry so they do not collide with one another.
        """
        self.reads_total: Final = Counter(
            "feature_flag_reads_total",
            "Times FeatureFlagService.get_flag was called.",
            registry=registry,
        )
        self.writes_total: Final = Counter(
            "feature_flag_writes_total",
            "Times FeatureFlagService.set_flag persisted a flag.",
            registry=registry,
        )
