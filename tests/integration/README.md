# integration

Tests that exercise a **service** against real Redis and PostgreSQL.

## Belongs here

Testcontainers starts throwaway `postgres:17-alpine` and `redis:7-alpine` (the same images as
local Compose), on random host ports so they cannot collide with Compose. That
startup is the session fixture `throwaway_stores` in
[`../conftest.py`](../conftest.py) (modules
[`throwaway_stores.py`](../throwaway_stores.py),
[`alembic_upgrade.py`](../alembic_upgrade.py)), shared with e2e. Alembic points
`POSTGRES__*` / `REDIS__*` at the containers so `alembic/env.py` cannot hit
Compose, then restores the process environment. [`conftest.py`](conftest.py) is
fixtures only.

Construct the service with real `RedisClient` and `PostgresClient` from
[`conftest.py`](conftest.py). The next service should reuse those fixtures rather than
start its own containers.

## Isolation

Redis `FLUSHDB` in the integration conftest (any service). Table
truncates belong next to the service that owns the table — feature flags wipe
`feature_flags` in [`services/feature_flag_service/conftest.py`](services/feature_flag_service/conftest.py).
`alembic_version` is left alone.

## Does not belong here

This is not HTTP. Routers, middleware, and `LifecycleManager` stay out.
Docker Desktop must be running. If the daemon is down, these tests skip.
In-process tests (buffers, temp files, `AsyncMock`) belong in
[`../unit/`](../unit/README.md). Cross-layer HTTP belongs in
[`../e2e/`](../e2e/README.md).
