# lifecycle

The composition root. This is the only place that constructs dependencies and wires them to each
other, and the only place that knows the order resources must start and stop in.

## Belongs here

- `LifecycleManager`, which builds the application (`create_app`) and installs the
  process `sys.excepthook` (`install_sys_excepthook`) and the uvicorn error and
  access bridges (`install_uvicorn_error_logging`,
  `install_uvicorn_access_logging`). Callers import
  `from app.lifecycle import LifecycleManager`.
- The startup and shutdown hooks that fill and later tear down `AppState`.

## Does not belong here

- Business logic, HTTP handlers, or anything that reads configuration from the environment.
  `LifecycleManager` is constructed with an already-validated `AppConfig`; it never builds one.

## Why a composition root

Every component declares its dependencies in its `__init__` and receives them. Something has to
actually construct that graph, and concentrating it in one place is what keeps it out of everywhere
else. Nothing outside this package calls a constructor for a client, a service, or a logger, which
is what makes the rest of the codebase free of global state and testable without patching.

`LifecycleManager` is a class rather than a set of functions because every construction step wants
the same two things, the configuration and a logger. It builds its own `LogManager` and child logger
in `__init__`, so each step can report what it is doing without that being threaded through six
signatures. `main.py` builds exactly one `LifecycleManager`, calls
`install_sys_excepthook()` then `install_uvicorn_error_logging()` then
`install_uvicorn_access_logging()`, then `create_app()`. `create_app` registers
`make_unhandled_http_exception_handler` on `Exception` with the same `uvicorn`
child the error bridge uses. The asyncio hook is installed for the lifespan of
the running loop. Access install is a no-op when
`LOGGER__ENABLE_UVICORN_ACCESS_LOGS` is false.

## Ordering

Startup runs in topological order: a resource is opened only after everything it depends on is.
Shutdown runs the exact reverse, so a resource is closed only once everything that might still call
it is gone. Declare fields in `AppClients` in that same order, so the code reads as the contract.

Construction and connection are separate steps. `_build_app_state` runs before there is an event
loop, so anything needing one opens in `_init_by_topological_order` instead.

The log manager is flushed last. Everything else logs through it, so draining it earlier would
discard the records written during the rest of the shutdown.

## HTTP registration

Register HTTP concerns in `_add_middlewares_in_order` and `_register_routers`. Starlette
wraps middleware in reverse order — last added is outermost — see
[`middlewares/`](../middlewares/README.md). This package's order is
`PrometheusManager.add_middleware(app)` first (innermost), then `SecureASGIMiddleware`,
then `CorrelationIdMiddleware` last (outermost). `add_metrics_router(app, config)`
mounts `GET /metrics` from `_register_routers`. Gzip comes from `PrometheusConfig`.
OpenAPI omission of `/metrics` is fixed in `PrometheusManager`. Each HTTP-aware custom
series is registered here so `PrometheusManager` does not catalog them.

Third-party `instrument(app)` / `setup(app)` helpers often call `add_middleware`
themselves. If that runs after `create_app()` returns, the library becomes outermost —
or sits outside the FastAPI stack entirely if it wraps the app object. Register those
libraries in `_add_middlewares_in_order`, in the intended slot.

## Typed application state

FastAPI keeps application state in an untyped bag whose attribute access returns `Any`. Reading it
directly would spread `Any` through every caller and silently switch off type checking.

`AppState` lives in [`state/`](../state/README.md), below this package so route handlers can
`Depends` on the accessors without importing the composition root. `LifecycleManager` is still
the only thing that constructs it. `get_app_state_from_app` is the single function in the
codebase that casts. Route handlers should reach for `get_app_services`: handlers call services,
and needing a raw client in a handler means the logic belongs in a service instead.
