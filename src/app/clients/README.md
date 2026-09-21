# clients

Clients for external resources: the application's data access layer.

## Belongs here

- One client class per resource, in a file named after that resource.
- Connection pools, query helpers, and the thin wrappers around Redis, PostgreSQL, and third-party
  APIs.

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.clients import PostgresClient, RedisClient`. The PostgreSQL subpackage
also re-exports `FeatureFlagRow` for the service layer:
`from app.clients.postgres import FeatureFlagRow`. Modules inside a client
package still import siblings by module path.

## Does not belong here

- Business logic. A client executes a command against one resource; it does not decide whether
  that command should run. That belongs in a service.
- HTTP. A client never imports FastAPI or Starlette. A Redis client that knows about request
  objects is the canonical layering violation.
- Configuration loading. A client is constructed with an already-validated config model; it never
  reads the environment.
- Schema migrations. Alembic lives at the repo root (`alembic/`, `alembic.ini`) and builds its
  own engine. Clients do not call `create_all` or run revisions.

## Dependency injection

A client declares its config and a child logger in its `__init__`. The composition root constructs
it once, starts it in topological order, and stores it on `AppClients`. A client never constructs
another client, reaches for a global, or builds its own logger.
