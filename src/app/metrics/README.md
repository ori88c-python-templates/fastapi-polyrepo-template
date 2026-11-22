# metrics

Prometheus collectors that do not read the HTTP request. Callers import
`from app.metrics import EventLoopLagMonitor, FeatureFlagMetrics`.

This package talks to [`prometheus_client`](https://github.com/prometheus/client_python)
and, for the event-loop probe, `asyncio`. It must not import FastAPI or Starlette.

It is not [`prometheus/`](../prometheus/README.md). That sibling of `routes/` and
`middlewares/` owns the scrape endpoint and HTTP-aware series. This package owns
collectors the composition root registers on that same registry.

## Table of Contents

- [Three kinds of custom metric](#three-kinds-of-custom-metric)
- [Dependency injection](#dependency-injection)

## Three kinds of custom metric

- **HTTP-aware** (request headers, status, path): defined in
  [`prometheus/`](../prometheus/README.md). The dummy series
  `http_requests_with_inbound_request_id_total` is the example.
- **Business** (a use case happened): defined here and injected into the service.
  The dummy series `feature_flag_reads_total` and `feature_flag_writes_total`
  are the example.
- **Runtime probe** (the process, not a request and not a use case): defined here.
  `EventLoopLagMonitor` samples `asyncio_event_loop_lag_seconds`. The composition
  root constructs it and starts and stops the probe with the running loop. A
  service does not increment it, and it does not read the request.

Default request latency and count come from
`prometheus_fastapi_instrumentator` and are wired in `LifecycleManager`, not here.

## Dependency injection

A collector is constructed once, on the same `CollectorRegistry` the `/metrics`
endpoint scrapes, and passed into the component that increments it. Components do
not call `Counter(...)` themselves: that would register a process-wide global.
The composition root always passes `PrometheusManager.registry`; there is no
default to the process-wide `REGISTRY`.

`EventLoopLagMonitor` takes that same registry. Registering the histogram does
not need a loop. `LifecycleManager` calls `start()` first in
`_init_by_topological_order` and `stop()` last in
`_teardown_by_reverse_topological_order`, before the log flush, including when
client startup fails.
