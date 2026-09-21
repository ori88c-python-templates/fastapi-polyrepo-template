# e2e

HTTP through the real application: `LifecycleManager`, routers, middleware, and
throwaway Redis and PostgreSQL.

## Belongs here

Requests go in-process (`httpx` + ASGI), not through a uvicorn subprocess. Lifespan
starts the clients once for the session.

Throwaway stores and Alembic `upgrade head` are the session fixture
`throwaway_stores` in [`../conftest.py`](../conftest.py) (modules
[`throwaway_stores.py`](../throwaway_stores.py),
[`alembic_upgrade.py`](../alembic_upgrade.py)). Integration tests share that
pair. `AppConfig` is built from those store configs so Compose `.env` is never
the DSN.

Layout mirrors `src/app/routes/`. The next router is
`tests/e2e/routes/<name>_router/`. Reuse `client` from
[`conftest.py`](conftest.py); do not start another app (the process-wide
Prometheus registry cannot register the same series twice). Each test module sets
`pytestmark = pytest.mark.asyncio(loop_scope="session")` so HTTP uses the same
event loop as the session-scoped clients.

Feature-flag tests scrape `GET /metrics` after a product request so custom
`feature_flag_*_total` series and default `http_requests_total` are observed on
the same process. Table truncates belong next to the router that owns the table.

## Does not belong here

Docker Desktop must be running. If the daemon is down, these tests skip.
Service-only tests belong in [`../integration/`](../integration/README.md).
In-process tests (buffers, temp files, `AsyncMock`) belong in
[`../unit/`](../unit/README.md).
