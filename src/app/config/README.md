# config

Pydantic models describing the application's configuration, and immutable protocol
constants that must not be overridden by the environment.

Nothing else belongs here: no clients, no I/O, no reading of `os.environ` outside the
settings machinery.

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.config import AppConfig, LoggerConfig, REQUEST_ID_HEADER, APP_NAME`. `AppConfig` still
composes sibling modules by their module path; it must not import `from app.config
import …`.

## Shape

`AppConfig` is the root. It is a composition of one model per resource, so each resource owns its
own validation and can be constructed on its own in a test:

```
AppConfig
├── ENV                       Environment: local | dev | staging | prod
├── server        ServerConfig        HOST, PORT
├── logger        LoggerConfig        MIN_LOG_LEVEL, ENABLE_UVICORN_ACCESS_LOGS
├── redis         RedisConfig         HOST, PORT, DB, PASSWORD, USE_TLS,
│                                     CONNECT_TIMEOUT_SECONDS, COMMAND_TIMEOUT_SECONDS
├── postgres      PostgresConfig      HOST, PORT, DATABASE, USER, PASSWORD, SSL_MODE,
│                                     CONNECT_TIMEOUT_SECONDS, STATEMENT_TIMEOUT_MS,
│                                     POOL_TIMEOUT_SECONDS
├── feature_flag  FeatureFlagConfig   CACHE_TTL_SECONDS
└── prometheus    PrometheusConfig    SHOULD_GZIP
```

`Environment.include_probes_in_schema()` is derived from `ENV`: Kubernetes probes
appear in OpenAPI for `local` and `dev` only. There is no extra environment variable.
`GET /metrics` is never in OpenAPI.

[`app_consts.py`](app_consts.py) holds header names, unprefixed infrastructure paths
(`REQUEST_ID_HEADER`, `/livez`, `/readyz`, `/metrics`, `/docs`, `/redoc`), and the log `app` identity
(`APP_NAME`). They are a contract with kubelet, Prometheus, inbound tracing, and
observability. They are not in `.env`: a typo there would break every probe, scrape,
or Grafana filter.

## Conventions

- Field names are `ALL_CAPS` so they read the same in code as they do in the environment.
- A duration, timeout, or TTL is an `int` whose name ends in `_SECONDS` or `_MS` for the unit
  the downstream API actually takes (`REDIS__CONNECT_TIMEOUT_SECONDS`,
  `POSTGRES__STATEMENT_TIMEOUT_MS`). Do not use `timedelta`, and do not convert under the
  hood (no seconds-to-ms multiply).
- Only `AppConfig` inherits from `BaseSettings`; the resource models are plain `BaseModel`s.
- Environment variables follow the nested model path, joined by `__`, so
  `AppConfig.postgres.HOST` comes from `POSTGRES__HOST`. Matching is case-insensitive.
- Secrets are `SecretStr`, which keeps them out of reprs and `model_dump()`.
- Assembled connection URLs are exposed as plain `@property` values, never `computed_field`, so
  they are not serialised along with the model and cannot leak a password into a log line.

## Validation

Configuration is validated once, at construction, so a bad deployment fails at startup instead of
at first use. Prefer Pydantic's built-in constraints over hand-written checks:

- Range and length constraints via `Field(ge=..., le=..., min_length=...)`.
- Closed sets via `StrEnum` (`Environment`, `LogLevel`) or `Literal` (`SSL_MODE`).
- Rules that span more than one field or model via `@model_validator(mode="after")`. `AppConfig`
  uses one to reject settings that are individually legal but wrong for production, such as
  `LOGGER__MIN_LOG_LEVEL=debug` when `ENV=prod`, or `POSTGRES__SSL_MODE=disable`.

## Adding a resource

1. Add `<resource>_config.py` with a `BaseModel` holding only the settings that genuinely vary
   between deployments. Anything the client library already defaults well should stay defaulted.
2. Add the field to `AppConfig`. Omit a default if the resource is mandatory.
3. Document the new variables in `.env.example`.
