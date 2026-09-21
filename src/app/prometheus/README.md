# prometheus

HTTP Prometheus: the scrape endpoint, the instrumentator middleware, and custom series
that read the Starlette request.

This package is a sibling of [`routes/`](../routes/README.md) and
[`middlewares/`](../middlewares/README.md). None of the three imports another. Shared
header names and unprefixed paths live in [`config/app_consts.py`](../config/app_consts.py).

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.prometheus import PrometheusManager`. Modules inside this
package still import siblings by module path.

## Belongs here

- `PrometheusManager`: typed manager over `prometheus-fastapi-instrumentator`
  (`add_http_instrumentation`, `add_middleware`, `add_metrics_router`).
- One file per HTTP-aware custom series (an `add_http_instrumentation` callback).

`PrometheusManager` installs only the library's default HTTP metrics. The composition
root registers each product callback so the manager does not become a catalog.

## Does not belong here

- Collectors that services increment. Those live in [`metrics/`](../metrics/README.md) and
  must not import FastAPI or Starlette.
- ASGI middleware classes that are not the instrumentator. Those live in `middlewares/`.

## Registration

`LifecycleManager` constructs `PrometheusManager` and calls `add_http_instrumentation`
before any middleware is installed. `add_middleware(app)` runs first in
`_add_middlewares_in_order` (innermost). `add_metrics_router(app, config)` mounts
`GET /metrics` from `_register_routers`. Gzip comes from `PrometheusConfig`. The
scrape path is omitted from OpenAPI in `PrometheusManager`, not via config.
Extra HTTP callbacks after `add_middleware` are rejected: the library has already
captured the list.
