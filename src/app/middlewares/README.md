# middlewares

ASGI middleware: the other half of the HTTP layer, wrapping every request before it reaches a
router.

## Belongs here

- One middleware class per concern, in a file named after that concern.
- Cross-cutting HTTP behaviour: correlation ids, request logging, error translation,
  CORS. Authentication in this template is a FastAPI `Depends`, not an ASGI wrapper
  (see below).

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.middlewares import CorrelationIdMiddleware, SecureASGIMiddleware,
make_unhandled_http_exception_handler`. A
middleware module still imports siblings by module path.

`CorrelationIdMiddleware` is a raw ASGI wrapper (not `BaseHTTPMiddleware`). It binds
`correlation_id` with `structlog.contextvars.bound_contextvars` for the request, stores
the same id on `request.state`, accepts
`X-Request-ID` or `X-Correlation-ID` inbound, and always returns `X-Request-ID`. Header
names come from [`config/app_consts.py`](../config/app_consts.py).

`make_unhandled_http_exception_handler` is FastAPI's `Exception` handler: it logs
through a `uvicorn` child logger and returns Starlette's generic `500 Internal Server Error`.
It is not middleware; `LifecycleManager.create_app` registers it with
`add_exception_handler`.

`SecureASGIMiddleware` is an adapter around the `secure` package's ASGI wrapper,
configured with `Secure.with_default_headers()`. FastAPI cannot attach ASGI
middleware to selected routes, and the library has no exclude list, so the adapter
is global. On `/docs` and `/redoc` it omits only `Content-Security-Policy`: FastAPI's
default Swagger UI and ReDoc HTML load jsDelivr plus an inline bootstrap that
BALANCED `script-src 'self'` would block. Every other BALANCED header still applies.
Path constants live in [`config/app_consts.py`](../config/app_consts.py).

HTTP Prometheus (`add_middleware`, `add_metrics_router`, HTTP-aware series) lives in
[`prometheus/`](../prometheus/README.md), a sibling of this package. Collectors that
services increment live in [`metrics/`](../metrics/README.md).

## Does not belong here

- Business logic. Middleware inspects or annotates a request; it does not decide what the request
  means. That belongs in a service.
- Direct database or cache access. Middleware talks to services when it needs dependencies; it
  never reaches for a client.
- Knowledge of which routers exist. Middleware wraps the whole application. If a path must be
  exempted (skipping auth for `/livez`), the constant lives in
  [`config/app_consts.py`](../config/app_consts.py), not in a router.

## Registration

Middleware is constructed by `LifecycleManager` and registered in `_add_middlewares_in_order`.
Starlette wraps middleware in reverse registration order, so the last one added is outermost.
A middleware never installs itself.

A library's `instrument(app)` / `setup(app)` often calls `add_middleware` at the call
site. `PrometheusManager.add_middleware(app)` is the usual example: it is registered
**first** in `_add_middlewares_in_order` (innermost of the three).
`add_metrics_router` is a router and is called from `_register_routers`.

## Authentication

Recommended auth is a route `Depends` (`require_access_token` / `require_session`),
documented in [`state/README.md`](../state/README.md) and the root README. That keeps
probes and `/metrics` unauthenticated by omission, and keeps Redis/JWKS behind a
service the composition root constructed.

If a clone needs a uniform 401 before routing, add an ASGI wrapper here and register
it only in `LifecycleManager._add_middlewares_in_order`. Register it **before**
`CorrelationIdMiddleware` (that class stays last, so it stays outermost and every
log line — including a 401 — still has `correlation_id`). Exempt `LIVEZ_ENDPOINT`,
`READYZ_ENDPOINT`, and `METRICS_ENDPOINT` from
[`app_consts.py`](../config/app_consts.py); do not import routers to decide —
`middlewares/` and `routes/` are siblings, so that import is a cycle.
The wrapper talks to a service, never to `RedisClient`. Do not
`instrument(app)` / wrap the app in `main`.

## Sibling independence

`routes/`, `middlewares/`, and `prometheus/` sit in the same layer and must not import each
other. A shared path or header name moves down, not sideways.
