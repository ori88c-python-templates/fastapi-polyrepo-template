# routes

FastAPI routers: the application's HTTP surface.

## Belongs here

- One `APIRouter` per resource, in a file named after that resource, as a sibling
  under `routes/` (`feature_flag_router.py`, `k8s_probe_router.py`). Nest a router
  domain only when that domain grows a second module.
- Path operation functions, their status codes, and their `response_model` declarations.

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.routes import feature_flag_router, k8s_probe_router, RouteLogger`. A router
module still imports `RouteLogger` from `route_child_logger.py` by module path; importing
`from app.routes import RouteLogger` inside a router would cycle.

## Does not belong here

- Business logic. A route should validate its input, call a service, and shape the result. If a
  handler is growing branches, the logic belongs in a service.
- Direct database or cache access. Routes talk to services; services talk to resources.
- Request and response schemas — those live in [`models/`](../models/README.md).

## Dependency injection

Routes get their dependencies through FastAPI's `Depends`, resolved against the accessors in
[`state/`](../state/README.md). A handler never constructs a service, reaches for a global, or
builds its own logger.

If a route logs, the logger is a `RouteLogger` argument from
[`route_child_logger.py`](route_child_logger.py). That is the only way a handler may log: no
`get_child_logger` inside the function, no module-level logger, no grabbing `LogManager` off
state. Services still receive a constructor-injected logger named after the service; the same
request can therefore emit two `context` values with one `correlation_id`.

Probe handlers stay dependency-free and do not log. Probe paths come from
[`config/app_consts.py`](../config/app_consts.py).

## OpenAPI

`summary=` and `description=` on the path decorator are the public contract shown
in `/docs`. The handler's Google docstring is for developers reading the code and
is not copied into OpenAPI.

Keep `name=` for [`RouteLogger`](route_child_logger.py); set `operation_id=`
separately so Swagger does not display the log name.

Kubernetes probes stay mounted for kubelet in every environment. They are omitted
from the schema when `ENV` is `staging` or `prod`.

## Unhandled errors

Anything the handler does not turn into `HTTPException` (Postgres, Redis, network)
becomes Starlette's generic `500 Internal Server Error`. Do not wrap it as
`HTTPException(500, detail=str(exc))`: that would put driver messages in the body.

## Sibling independence

`routes/`, `middlewares/`, and `prometheus/` sit in the same layer and must not import each
other. A shared path or header name moves down, not sideways.

