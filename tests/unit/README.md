# unit

In-process tests only.

## Belongs here

Dependencies are passed in: a `BytesIO` for the log manager, an `AsyncMock` for a client the
handler does not need to exercise, a temp file for encoding checks. Injecting a dependency is
fine: a buffer, a temp file, an in-memory implementation, or an `AsyncMock` constructed and
handed to `AppState`. That is dependency injection, not patching.

Layout mirrors `src/app/`: one directory per package, then one directory per component
under test, then one file per feature.

```
routes/          feature_flag_router, k8s_probe_router, route_child_logger
middlewares/     correlation_id_middleware, secure_headers, unhandled_http_exception_handler
prometheus/      HTTP metrics wiring (the package is the component)
services/        feature_flag_service
logger/          log_manager, asyncio_exception_handler, sys_excepthook,
                 uvicorn_access_log_handler, uvicorn_error_log_handler,
                 uvicorn_asgi_exception_filter
config/          app_config, logger_config, redis_config, postgres_config,
                 feature_flag_config
distribution/    installed_app_version
clients/         redis_client, postgres_client
```

## Does not belong here

A unit test never opens a socket to Redis or PostgreSQL, never starts the
real application lifespan against those servers, and never starts Docker.
`unittest.mock.patch` and `monkeypatch` are still forbidden.
