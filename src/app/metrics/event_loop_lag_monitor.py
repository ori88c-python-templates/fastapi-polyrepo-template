"""Histogram of how late the asyncio loop runs a due callback."""

import asyncio
import contextlib
from typing import Final

from prometheus_client import CollectorRegistry, Histogram

_DEFAULT_INTERVAL_SECONDS: Final = 0.1
_NON_NEGATIVE_LAG_SECONDS: Final = 0.0
_TASK_NAME: Final = "event-loop-lag"
_METRIC_NAME: Final = "asyncio_event_loop_lag_seconds"
# Sub-millisecond stalls are noise. Buckets start at 1ms so a request-latency
# ladder, which usually opens at 5-10ms, cannot hide the stalls this series is for.
_BUCKETS_SECONDS: Final = (
    0.001,
    0.0025,
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
)
_METRIC_HELP: Final = (
    "Seconds a scheduled callback ran after it was due. "
    "Near zero on an idle loop. Rises when synchronous work or a backlog of "
    "ready callbacks occupies the loop thread. Does not name the callback."
)


class EventLoopLagMonitor:
    """Samples asyncio scheduling delay into one unlabeled histogram.

    A due callback that runs late is the signal that the loop thread was busy.
    Synchronous blocking, a long CPU callback, and a pile of already-ready
    coroutines all look the same here; the series does not identify which.

    A stall shorter than the sample interval is recorded only when it overlaps
    a wakeup. The default interval is a tenth of a second: often enough to see
    stalls of tens of milliseconds, cheap enough to leave on. The interval is
    not configuration. A deployment that stretched it would miss the stalls.

    Constructed by the composition root on ``PrometheusManager.registry``.
    ``start`` needs a running loop and belongs in the lifespan, not in
    ``__init__``.

    Attributes:
        lag_seconds: Observations of scheduling delay, in seconds.
    """

    def __init__(
        self,
        registry: CollectorRegistry,
        *,
        interval_seconds: float = _DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        """Register the histogram. Does not start the probe.

        Args:
            registry: Collector to register with. Must be the registry
                ``PrometheusManager`` scrapes. There is no default: omitting
                it would publish on the process-wide registry.
            interval_seconds: Seconds between wakeups. Production uses the
                default. Tests pass a shorter interval.
        """
        self._interval_seconds: Final = interval_seconds
        self.lag_seconds: Final = Histogram(
            _METRIC_NAME,
            _METRIC_HELP,
            buckets=_BUCKETS_SECONDS,
            registry=registry,
        )
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Schedule the probe on the running loop.

        Raises:
            RuntimeError: If the probe is already running, or if there is no
                running event loop for ``asyncio.create_task``.
        """
        if self._task is not None:
            raise RuntimeError("Event loop lag monitor is already started.")
        self._task = asyncio.create_task(self._sample(), name=_TASK_NAME)

    async def stop(self) -> None:
        """Cancel the probe and wait until it has left the loop.

        A second call does nothing, so lifespan teardown can run after a
        startup failure that never reached ``start``. Cancellation during
        ``asyncio.sleep`` is not recorded: the sleep raises before ``observe``.
        """
        task = self._task
        if task is None:
            return
        self._task = None
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _sample(self) -> None:
        """Record how late each wakeup was, until cancelled.

        ``loop.time`` is the clock the scheduler uses, including under uvloop.
        The overrun is ``now - due``, not the full sleep, so an idle loop stays
        near zero. A wakeup can be a moment early. A negative observation is
        legal for the client, but Prometheus reads a falling sum as a counter
        reset, so that sample is recorded as zero.
        """
        loop = asyncio.get_running_loop()
        interval = self._interval_seconds
        while True:
            due = loop.time() + interval
            await asyncio.sleep(interval)
            lag = loop.time() - due
            self.lag_seconds.observe(max(lag, _NON_NEGATIVE_LAG_SECONDS))
