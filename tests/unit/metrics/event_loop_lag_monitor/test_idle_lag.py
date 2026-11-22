"""An idle loop records scheduling delay, not the length of the probe sleep."""

import asyncio

from prometheus_client import CollectorRegistry

from app.metrics import EventLoopLagMonitor
from tests.unit.metrics.event_loop_lag_monitor.helpers import sample_value

_INTERVAL_SECONDS = 0.1
_IDLE_SECONDS = 0.35
# Half the sample interval. A sample this large is still the overrun, not the sleep.
_WELL_UNDER_LE = "0.05"


async def test_idle_loop_records_lag_below_the_sample_interval() -> None:
    """Samples land, and every one of them stays well under the interval.

    The probe observes how late the wakeup was. On an idle loop that overrun
    stays near zero, so a histogram that stored the sleep itself would fail.
    """
    registry = CollectorRegistry()
    monitor = EventLoopLagMonitor(registry, interval_seconds=_INTERVAL_SECONDS)
    monitor.start()
    try:
        await asyncio.sleep(_IDLE_SECONDS)
    finally:
        await monitor.stop()

    count = sample_value(registry, "_count")
    within = sample_value(registry, "_bucket", le=_WELL_UNDER_LE)
    assert count >= 2
    assert within == count
