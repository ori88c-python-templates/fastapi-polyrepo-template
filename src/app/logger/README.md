# logger

Structured JSON logging built on [structlog](https://www.structlog.org/).

## Belongs here

- `LogManager`, which hands out named child loggers via `get_child_logger(name)`.
- The asyncio and `sys.excepthook` factories, `UvicornLogHandler` (rewrites
  `uvicorn.error` and `uvicorn.access` records as JSON), and `UvicornAsgiExceptionFilter`
  (kept so a handled HTTP 500 is not indexed twice).

Callers import `from app.logger import LogManager`.

## Does not belong here

- `LoggerConfig`. Leaf modules still import it from `app.config`, not from this
  package's `__init__.py`.

## Rule

There is no global logger, and no module-level logger instance either. A component receives its
logger as a constructor argument:

```python
class UsersService:
    def __init__(self, logger: FilteringBoundLogger) -> None:
        self._logger = logger


# in the composition root
log_manager = LogManager(config.logger, env=config.ENV, app_version=app_version)
users_service = UsersService(log_manager.get_child_logger("UsersService"))
```

If a route logs, it does not call `get_child_logger` itself and does not take a `LogManager` off
application state. The logger is a `RouteLogger` argument — a `Depends` in
[`routes/route_child_logger.py`](../routes/route_child_logger.py) that names the child after the
matched route's FastAPI `name=`.

That `name=` is FastAPI's route identity (`url_path_for`, `request.scope["route"].name`).
`RouteLogger` copies it into the log `context` field. Set it explicitly so `context` stays
stable when the handler function is renamed. Do not invent a `logger_context=` parameter —
FastAPI has no such kwarg. The path parameter `{name}` is the resource identifier and is
unrelated to the decorator's `name=`.

```python
@feature_flag_router.get("/{name}", name="feature-flag-router.get")
async def get_feature_flag(
    name: str,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    logger: RouteLogger,
) -> FeatureFlag:
    logger.info("feature_flag.get", name=name)
    return await service.get_flag(name)
```

```json
{"name": "dark_mode", "context": "feature-flag-router.get", "level": "info", "ts": "2026-09-11T13:12:00.000000Z", "msg": "feature_flag.get", "correlation_id": "6f1d3c2a-9b4e-4c11-8a2f-0e7b1d4a9c33", "env": "dev", "app": "fastapi-polyrepo-template", "instance": "api-1", "app.version": "1.0.0"}
```

`correlation_id` is bound by `CorrelationIdMiddleware` for the request, not by the route. The
processor chain already runs `structlog.contextvars.merge_contextvars` first, so every child
logger on that request — route, service, client — includes the same id. `env`, `app`,
`instance`, and `app.version` are stamped by `LogManager` on every record.

This is enforced by [.cursor/rules/logging.mdc](../../../.cursor/rules/logging.mdc).

## Hooks and bridges

`structlog.configure()` is not used as a global hook. Each surface closes over a
`LogManager` child from `wrap_logger()`. Grafana filters on `context`.

### Uncaught exceptions

- `make_unhandled_http_exception_handler` (`context="uvicorn"`) — FastAPI `Exception`
  handler. The generic 500 body stays `Internal Server Error`. Starlette re-raises;
  uvicorn would emit unstructured `Exception in ASGI application` on `uvicorn.error`;
  `UvicornAsgiExceptionFilter` drops that duplicate.
- `make_asyncio_exception_handler` (`context="asyncio"`) — `loop.set_exception_handler`
  for the lifespan of the app. This is the asyncio loop hook, not a uvicorn logger.
- `make_sys_excepthook` (`context="sys.excepthook"`) — installed from `main`, not
  from `create_app`.

Awaited lifespan/startup failures are caught by uvicorn and are not uncaught; these
hooks do not see them.

### Uvicorn bridges

Bridged uvicorn stdlib loggers (event string is uvicorn's sentence, not a dotted app
event):

- `context="uvicorn"` — `uvicorn.error` (startup, shutdown, warnings, errors,
  critical). That logger is not error-only. Same child as the HTTP 500 hook.
  `LifecycleManager.install_uvicorn_error_logging()` (from `main`, not `create_app`)
  attaches `UvicornLogHandler` and the ASGI filter with `propagate=False`, and
  sets the stdlib logger to DEBUG. `uvicorn.run(..., log_config=None)` skips
  uvicorn's `dictConfig` that would otherwise set that level; without it, root
  WARNING swallows INFO startup lines before the handler runs. A single-process
  run emits these `msg` values, in order: `Started server process`, `Waiting
  for application startup.`, `Application startup complete.`, `Uvicorn running
  on …`, then on stop `Shutting down`, `Waiting for application shutdown.`,
  `Application shutdown complete.`, `Finished server process`.
- `context="uvicorn.access"` — `uvicorn.access` when
  `LOGGER__ENABLE_UVICORN_ACCESS_LOGS` is true (default).
  `LifecycleManager.install_uvicorn_access_logging()` is a no-op when the flag is
  false; `main` also passes `access_log=` so uvicorn emits nothing. Access is
  logged on `http.response.start` while `CorrelationIdMiddleware` still holds
  contextvars, so `correlation_id` is merged automatically. Install also sets
  the stdlib `uvicorn.access` logger to DEBUG for the same `log_config=None`
  reason as `uvicorn.error`. Opening `/docs` also logs `GET /openapi.json`; that
  is Swagger fetching the spec, not a third product route.

Tests construct `UvicornAsgiExceptionFilter` / `UvicornLogHandler` and call
`.filter` / `.emit` without installing on the process logger.
`test_install.py` attaches to `uvicorn.error` / `uvicorn.access` and restores
handlers, filters, level, and propagate in `finally`.
`uvicorn.run(..., log_config=None)` keeps uvicorn's default `dictConfig` from
wiping the handlers.

## One instance, but not a singleton

An application has exactly one `LogManager`. A second one would just be a second pipeline writing
to the same stream under a different configuration, which nothing wants.

That single instance is a consequence of the wiring, not something the class enforces. `LogManager`
is deliberately *not* a singleton: the singleton pattern would put it back in global state and
recreate the import-order coupling this design exists to avoid. Construct it once in the
composition root and pass it down. Tests construct as many as they need.

## Why no `structlog.configure()`

`structlog.configure()` installs process-wide defaults. That is the global state this codebase
exists to avoid: logging behaviour would depend on import order, and a test that wanted a different
configuration would have to install it globally and then undo it. `LogManager` uses
`structlog.wrap_logger()` instead, which structlog documents as the way to use it "without any
global state". Two `LogManager` instances with different minimum levels can coexist in one process
without interfering — which is what makes logging testable.

## Output

One JSON object per line, on stdout:

```json
{"user_id": 42, "env": "dev", "app": "fastapi-polyrepo-template", "instance": "api-1", "app.version": "1.0.0", "context": "UsersService", "level": "info", "ts": "2026-09-05T16:11:04.812733Z", "msg": "user.created"}
```

- `ts` — ISO 8601 / RFC 3339 in UTC with a `Z` suffix, which Datadog, ELK and Cloud Logging all
  parse natively. Renamed from structlog's default `timestamp`.
- `msg` — the log message. Renamed from structlog's default `event` by `EventRenamer`, which must
  stay immediately before the renderer since earlier processors read the `event` key.
- `context` — the name passed to `get_child_logger`, i.e. the component that emitted the record.
- `level` — the canonical level name.
- `env` — `AppConfig.ENV` (`local` / `dev` / `staging` / `prod`). Passed into `LogManager`, not
  read from `LoggerConfig`.
- `app` — `APP_NAME` in [`app_consts.py`](../config/app_consts.py). Hardcoded identity; not
  overridable in `.env`.
- `instance` — `socket.gethostname()` once when the manager is constructed.
- `app.version` — injected by the composition root from `app.distribution`
  (`installed_app_version`). Installed metadata for the dist that provides the
  `app` import (`importlib.metadata`, populated from `pyproject.toml` at
  install). Not a string parsed from the toml file at runtime. `LogManager`
  only stamps the string it is given, same as `env`.
- `correlation_id` — present on records emitted during an HTTP request. Bound by
  `CorrelationIdMiddleware` via structlog contextvars for in-request loggers. The
  unhandled HTTP handler sits outside that context manager and passes the id as a
  kwarg from `request.state`.

Both renames happen once, in `LogManager._set_property_names()`.

## UTF-8

Records are encoded once, in the renderer, and written as bytes: `_serialize()` calls
`json.dumps(..., ensure_ascii=False).encode("utf-8")`, and `structlog.BytesLogger` writes the result
to a binary stream.

Encoding at the renderer rather than at the stream is what makes the output UTF-8 everywhere. A text
stream encodes using the platform's locale, which on Windows is still a legacy code page that raises
`UnicodeEncodeError` on most of Unicode. Bypassing the text layer removes that variable entirely —
`tests/unit/logger/log_manager/test_stdout.py` proves it by forcing `PYTHONIOENCODING=cp1252` and asserting the
output is still UTF-8.

The one trade-off: writing to `sys.stdout.buffer` bypasses the text layer's buffer, so log records
can appear out of order relative to plain `print()`. Do not mix the two; if something is worth
putting on stdout, log it.

## Output stream

`LogManager(config, env=..., app_version=..., stream=...)` takes the deployment
`Environment`, the installed app version, and an optional binary stream, defaulting
to `sys.stdout.buffer`. Production looks the version up once and injects it; it
passes nothing for the stream. Tests pass a `BytesIO` or an open file, which is how
the suite asserts against real bytes instead of a mocked writer.

`flush()` drains the stream. Records are already flushed as they are written, so it only matters on
graceful shutdown. It does not close the stream — `LogManager` does not own stdout.

## Levels

`LoggerConfig.MIN_LOG_LEVEL` is a `LogLevel` enum whose members are exactly structlog's canonical
level names, so the level is validated by Pydantic at startup rather than by structlog at first
use. Filtering uses `structlog.make_filtering_bound_logger`, which discards records below the
minimum level before any processor runs. `ENABLE_UVICORN_ACCESS_LOGS` is not applied by
`LogManager`; `main` and `LifecycleManager` install or skip the access bridge.
