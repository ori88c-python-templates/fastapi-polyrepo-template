# services

Business services: the application's service layer.

## Belongs here

- One service class per use case, in a subdirectory named after that use case:
  `services/feature_flag/feature_flag_service.py`. The basename still names the
  concept, so grep and tracebacks stay readable.
- Service-layer exceptions in a sibling `*_errors.py` in that same directory, not
  in the service module. A service that grows more than one error should not
  force those types to live next to the business methods.
- Orchestration that a route would otherwise grow branches for: validation that spans models,
  coordinating clients, deciding what to persist.

Public types are re-exported from [`__init__.py`](__init__.py), so callers import
`from app.services import FeatureFlagService` rather than the nested path. Modules
inside this package still import siblings by module path; `from app.services import …`
inside a service module would cycle through that same `__init__.py`.

## Does not belong here

- HTTP. A service never imports FastAPI or Starlette, never reads a `Request`, and never returns
  a `Response`. Those belong in a router.
- Raw resource access that is not already wrapped in a client. A service calls `clients/`; it
  does not construct a Redis connection or open a SQLAlchemy session.
- Request and response schemas — those live in [`models/`](../models/README.md).

## Dependency injection

A service declares every dependency in its `__init__`: the clients it needs, a child logger
named after itself, and any Prometheus collectors it increments (`FeatureFlagMetrics`).
The composition root constructs those once and stores the service on `AppServices`. A
service never constructs a client, reaches for a global, or builds its own logger.
