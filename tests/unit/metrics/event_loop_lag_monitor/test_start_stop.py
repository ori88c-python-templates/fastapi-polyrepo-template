"""The probe task starts once and does not outlive ``stop``."""

import asyncio

import pytest
from prometheus_client import CollectorRegistry

from app.metrics import EventLoopLagMonitor

_TASK_NAME = "event-loop-lag"


async def test_stop_cancels_the_probe_and_is_idempotent() -> None:
    """``stop`` before ``start``, and a second ``stop``, both leave no probe task."""
    monitor = EventLoopLagMonitor(CollectorRegistry(), interval_seconds=0.05)
    await monitor.stop()

    monitor.start()
    await asyncio.sleep(0)
    await monitor.stop()

    running = {task.get_name() for task in asyncio.all_tasks()}
    assert _TASK_NAME not in running
    await monitor.stop()


async def test_start_twice_raises() -> None:
    """A second ``start`` is a mistake, not a second probe."""
    monitor = EventLoopLagMonitor(CollectorRegistry(), interval_seconds=0.05)
    monitor.start()
    try:
        with pytest.raises(RuntimeError, match="already started"):
            monitor.start()
    finally:
        await monitor.stop()
