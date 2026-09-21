# metrics

Prometheus collectors that **services and clients** increment. Callers import
`from app.metrics import FeatureFlagMetrics`.

This package talks to [`prometheus_client`](https://github.com/prometheus/client_python)
only. It must not import FastAPI or Starlette.

It is not [`prometheus/`](../prometheus/README.md). That sibling of `routes/` and
`middlewares/` owns the scrape endpoint and HTTP-aware series. This package owns
collectors injected into services.

## Two kinds of custom metric

- **HTTP-aware** (request headers, status, path): defined in
  [`prometheus/`](../prometheus/README.md). The dummy series
  `http_requests_with_inbound_request_id_total` is the example.
- **Business** (a use case happened): defined here and injected into the service.
  The dummy series `feature_flag_reads_total` and `feature_flag_writes_total`
  are the example.

Default request latency and count come from
`prometheus_fastapi_instrumentator` and are wired in `LifecycleManager`, not here.

## Dependency injection

A collector is constructed once, on the same `CollectorRegistry` the `/metrics`
endpoint scrapes, and passed into the component that increments it. Components do
not call `Counter(...)` themselves: that would register a process-wide global.
The composition root always passes `PrometheusManager.registry`; there is no
default to the process-wide `REGISTRY`.
