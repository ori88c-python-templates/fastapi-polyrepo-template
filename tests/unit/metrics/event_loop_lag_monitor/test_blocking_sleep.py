"""Synchronous work on the loop thread is visible in the lag histogram."""

import asyncio
import time

from prometheus_client import CollectorRegistry

from app.metrics import EventLoopLagMonitor
from tests.unit.metrics.event_loop_lag_monitor.helpers import sample_value

_INTERVAL_SECONDS = 0.05
_BLOCKED_SECONDS = 0.2


async def test_blocking_sleep_is_recorded_as_lag() -> None:
    """A ``time.sleep`` that overlaps the probe is about the histogram sum.

    The probe is already waiting, so the recorded overrun is the block minus
    the one interval it had left to sleep. Waiting a short positive interval
    afterwards lets that overdue timer run before the sum is read.
    """
    registry = CollectorRegistry()
    monitor = EventLoopLagMonitor(registry, interval_seconds=_INTERVAL_SECONDS)
    monitor.start()
    try:
        await asyncio.sleep(0)
        time.sleep(_BLOCKED_SECONDS)
        await asyncio.sleep(0.01)
    finally:
        await monitor.stop()

    total = sample_value(registry, "_sum")
    # The scheduled interval is not lag. A little slack covers timer jitter.
    assert total >= _BLOCKED_SECONDS - _INTERVAL_SECONDS - 0.02
