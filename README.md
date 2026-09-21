# FastAPI Polyrepo Template

[![CI](https://github.com/ori88c-python-templates/fastapi-polyrepo-template/actions/workflows/ci.yml/badge.svg)](https://github.com/ori88c-python-templates/fastapi-polyrepo-template/actions/workflows/ci.yml)
[![Audit](https://github.com/ori88c-python-templates/fastapi-polyrepo-template/actions/workflows/audit.yml/badge.svg)](https://github.com/ori88c-python-templates/fastapi-polyrepo-template/actions/workflows/audit.yml)

Production-grade FastAPI template built around **dependency injection** and **zero global state**.
A composition root wires clients, services, and loggers so tests inject dependencies instead of monkeypatching; Cursor rules keep AI edits copying this architecture. Layered import DAG, Testcontainers, Prometheus, and Kubernetes probes included.

## Table of Contents

- [Highlights](#highlights)
- [Why this template](#why-this-template)
- [Architecture](#architecture)
- [Layout](#layout)
- [Configuration](#configuration)
- [Logging](#logging)
- [Running locally](#running-locally)
- [Schema migrations](#schema-migrations)
- [Container image](#container-image)
- [Production deploy](#production-deploy)
- [Testing](#testing)
- [Linting and type checking](#linting-and-type-checking)
- [CI](#ci)
- [Authentication](#authentication)

## Highlights

- **Dependency injection, zero global state** 🧩: Every component takes dependencies in `__init__`; `LifecycleManager` (the composition root) constructs the clients, services, and loggers and wires them — `main.py` only builds `AppConfig` and that manager. No module-level config, logger, or client, so tests inject dependencies instead of monkeypatching or process-wide setup.
- **Three-layer import DAG, enforced** 🧭: HTTP (`routes` / `middlewares` / `prometheus`), services, and clients stay loosely coupled so you can test a service without FastAPI and a client without a route. Packages import downward only; `lint-imports` fails cycles and FastAPI leaking into services or clients.
- **Nested Pydantic config** ⚙️: `AppConfig` composes resource-specific models (`postgres`, `redis`, `logger`, `feature_flag`, …). Invalid config fails at startup, not on the first request.
- **Structured JSON logging** 📡: Every line carries prod-grade fields (`app`, `instance`, `env`, `app.version`, `correlation_id`). Each component gets a named child logger with its own `context`, so you can filter easily — with grep, or with observability tools such as Groundcover, Grafana, and Datadog.
- **Unit, integration, and e2e from day 1** 🧪: `pytest` is wired for all three: in-process units, Testcontainers against real Redis/PostgreSQL, and HTTP through `LifecycleManager`.
- **Cursor rules that keep the conventions** 🤖: Checked-in [`.cursor/rules`](.cursor/rules) encode layers, logging, tests, and metrics so AI-assisted edits copy this architecture instead of inventing a new one.
- **Sample vertical slice** 🚩: `FeatureFlagService` plus its router, Prometheus series, and matching integration and e2e tests. Copy that pattern for the first real resource.
- **Alembic out of band** 🗃️: Schema migrations are their own command, separate from the HTTP process. Same image, two commands: upgrade, then start the app.
- **Production-shaped ops** 🚢: Non-root multi-stage image, Kubernetes liveness and readiness probes (`GET /livez`, `GET /readyz`), Prometheus scrape (`GET /metrics`), and GitHub Actions CI. `FeatureFlagService` includes a custom-metrics example (`feature_flag_reads_total`, `feature_flag_writes_total`).
- **Supply-chain hygiene** 🔒: SHA-pinned Actions, weekly Dependabot for the `uv` lockfile and GitHub Actions, and a separate `uv audit` workflow on push/PR plus a weekly schedule so a CVE published while `main` is idle still fails the Audit badge.

## Why this template

Unlike opinionated application frameworks such as NestJS, Spring, and .NET, FastAPI does not
prescribe a strict architecture. Without widely shared project conventions, **tightly coupled
components, module-level globals, and related anti-patterns are common in Python codebases**, in
part because package docs favor short examples that use global state for brevity. The risk is
sharper in AI-assisted development: each existing pattern becomes the baseline the next
change copies. This template is a starting architecture that follows best practices from the
first commit, so you can spend the remaining effort on the product.

The guiding constraint: nothing important is reachable through a module-level global. No global
config object, no global logger, no import-time singletons. Every component declares what it needs
in its `__init__`, and a **single composition root** (`LifecycleManager`) wires those
dependencies together. That is what makes the code testable without monkeypatching and without
import-order surprises.

## Architecture

The application is a three-layer stack. Imports point downward only.

```
                         main.py
                            |
                       lifecycle/          composition root: builds the graph
                            |
   . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .
                            v
   HTTP layer          routes/  middlewares/  prometheus/
                                                FastAPI routers, ASGI middleware,
                                                scrape endpoint and HTTP-aware series
                                                siblings: none of the three imports another
   . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .
                            v
                       state/                  typed AppState + accessors
   . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .
                            v
   Service layer       services/               business logic
   . . . . . . . . . . . . .|. . . . . . . . . . . . . . . . . . . .
                            v
   Data access layer   clients/                redis, postgres, external APIs

   Imports point downward only. A client never imports a service, and never
   imports FastAPI.

   Cross-cutting, importable from any layer, importing none of them:
       models/     config/     logger/     metrics/     distribution/
```

A route calls a service; a service calls a client. A Redis client that imports FastAPI is the
canonical violation: it creates a cycle between the HTTP and data access layers.

`lifecycle/` is the one package allowed to import every layer — that is what a composition root is
for. `models/`, `config/`, `logger/`, `metrics/` and `distribution/` sit below everything so they
cannot import back up.

The import graph must stay a DAG. **Python tolerates cycles; this codebase does not**. Adding a new
top-level package fails the contract until it is placed in the hierarchy, so every insertion is
forced to declare where it sits. `uv run lint-imports` enforces both rules from `pyproject.toml`.

### Avoiding hidden cyclic dependencies

A cycle is not a style nit. Python will import `A` while `B` is still half-initialized, so
construction order becomes whoever got imported first instead of a decision the composition root
made. Tests then cannot build one dependency without dragging in the other, which is how suites
slide into monkeypatching and process-wide setup. The stack is a DAG so `LifecycleManager` can
start resources in topological order and tear them down in reverse; a cycle turns that into a race
of who exists before whom.

Import Linter only sees **directory-sized** layers: `services/` must not import `routes/`. Two
modules in the same package — `feature_flag_service.py` importing `orders_service.py` and back —
still compile, still pass `uv run lint-imports`, and are still a cycle. Same-layer packages listed
with `|` (`routes | middlewares | prometheus`) are the sibling set the linter does catch. Everything else
at one level is the developer's job.

## Layout

| Path | Contents |
| --- | --- |
| `src/app/config/` | Pydantic settings and immutable protocol constants |
| `src/app/lifecycle/` | The composition root: `LifecycleManager`, startup and shutdown |
| `src/app/state/` | Typed `AppState` and the accessors route handlers `Depends` on |
| `src/app/logger/` | `LogManager`, the factory for injectable structured child loggers |
| `src/app/metrics/` | Prometheus collectors injected into services; not FastAPI-aware |
| `src/app/distribution/` | Installed dist metadata for the `app` import (`app.version`) |
| `src/app/models/` | Shared Pydantic models used by services and routes |
| `src/app/clients/` | Data access clients for Redis, PostgreSQL, and external APIs |
| `src/app/services/` | Business services; the only layer routes and middleware depend on |
| `src/app/routes/` | FastAPI routers |
| `src/app/middlewares/` | ASGI middleware wrapping the HTTP surface |
| `src/app/prometheus/` | HTTP instrumentation: scrape endpoint and HTTP-aware series |
| `src/app/main.py` | Process entry point |
| `alembic/` | Migration environment and versioned revisions |
| `compose.yaml` | Local Redis and PostgreSQL only |
| `Dockerfile` | Production image: server by default, Alembic by command override |

Each `src/app/` directory has its own README explaining what belongs there.

## Configuration

Configuration is a composition of resource-specific Pydantic models under a single `AppConfig`
(see [src/app/config/README.md](src/app/config/README.md)). Environment variables follow the
nested model path, joined by `__`: `AppConfig.postgres.HOST` comes from `POSTGRES__HOST`.
`.env.example` documents every supported variable.

Validation is strict and fails at startup rather than at first use: ports are range-checked,
passwords are `SecretStr`, and cross-cutting rules (such as forbidding debug logging in production)
are enforced by model validators.

## Logging

Logging is structured JSON via [structlog](https://www.structlog.org/). `LogManager`
receives a `LoggerConfig` in its constructor and hands out named child loggers through
`get_child_logger(name)`. Components receive a logger as a constructor argument; they
never reach for a global one. Uncaught exceptions (`asyncio`, FastAPI `Exception`,
`sys.excepthook`) and uvicorn's `uvicorn.error` / `uvicorn.access` loggers are rewritten
as those children — `context` values and the `LOGGER__ENABLE_UVICORN_ACCESS_LOGS` flag
(default true) are documented in [src/app/logger/README.md](src/app/logger/README.md).
A start-to-stop process-lifetime transcript (no HTTP, so no `correlation_id`) is under
[Running locally](#running-locally).

## Running locally

### Requirements

- Python 3.14 (pinned in `.python-version`; `uv` can install it)
- [uv](https://docs.astral.sh/uv/) for dependency management
- [Docker Desktop](https://docs.docker.com/desktop/) (Compose v2) for local Redis and PostgreSQL

### Setup

```bash
uv sync
uv run pre-commit install
cp .env.example .env
```

`uv sync` installs the dev tools. `uv run pre-commit install` registers the Git hook once per
clone so commits run the checks in [Linting and type checking](#linting-and-type-checking).

`.env.example` is a working local configuration for the Compose stack, not a list of
placeholders. Copy it before `docker compose up` so Compose interpolation, Alembic, and the
app share one file. `.env` is git-ignored.

### Compose, migrate, serve

Compose is **local-only**: it runs Redis and PostgreSQL on loopback. The HTTP process stays on
the host so `.env` can keep `127.0.0.1` instead of Docker DNS names.

From the repository root:

```bash
docker compose up -d --wait
uv run alembic upgrade head
uv run app
```

Then open [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs). Kubernetes probes are
unprefixed `GET /livez` and `GET /readyz`. Prometheus scrapes unprefixed `GET /metrics`.

<details>
<summary>Example stdout from <code>uv run app</code> (structured JSON, one object per line)</summary>

```
{"context": "LifecycleManager", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.793853Z", "msg": "lifecycle.app.creating"}
{"context": "LifecycleManager", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.794233Z", "msg": "lifecycle.app_state.building"}
{"context": "LifecycleManager", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.949405Z", "msg": "lifecycle.middlewares.registering"}
{"context": "LifecycleManager", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.949974Z", "msg": "lifecycle.routers.registering"}
{"context": "uvicorn", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.991882Z", "msg": "Started server process [31796]"}
{"context": "uvicorn", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.992280Z", "msg": "Waiting for application startup."}
{"context": "LifecycleManager", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.992882Z", "msg": "lifecycle.resources.initializing"}
{"context": "RedisClient", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:41.993230Z", "msg": "redis.starting"}
{"context": "RedisClient", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:42.000426Z", "msg": "redis.started"}
{"context": "PostgresClient", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:42.000736Z", "msg": "postgres.starting"}
{"context": "PostgresClient", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:42.053945Z", "msg": "postgres.started"}
{"context": "uvicorn", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:42.054500Z", "msg": "Application startup complete."}
{"context": "uvicorn", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:42.055343Z", "msg": "Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)"}
{"context": "uvicorn", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.858121Z", "msg": "Shutting down"}
{"context": "uvicorn", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.965785Z", "msg": "Waiting for application shutdown."}
{"context": "LifecycleManager", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.966757Z", "msg": "lifecycle.resources.tearing_down"}
{"context": "PostgresClient", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.967397Z", "msg": "postgres.stopping"}
{"context": "PostgresClient", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.969456Z", "msg": "postgres.stopped"}
{"context": "RedisClient", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.970018Z", "msg": "redis.stopping"}
{"context": "RedisClient", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.970585Z", "msg": "redis.stopped"}
{"context": "uvicorn", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.971017Z", "msg": "Application shutdown complete."}
{"context": "uvicorn", "env": "local", "app": "fastapi-polyrepo-template", "instance": "MacBook-Pro.local", "app.version": "1.0.0", "level": "info", "ts": "2026-09-22T05:30:57.971357Z", "msg": "Finished server process [31796]"}
```

</details>

Stop the dependency stack with `docker compose down`. Add `-v` to wipe the Postgres volume; you
must `uv run alembic upgrade head` again after that.

Hosts in `.env` are `127.0.0.1`, not `localhost`, so Windows does not stall on IPv6 while Docker
Desktop publishes IPv4 only. Inside a container network, point `REDIS__HOST` / `POSTGRES__HOST` at
the service names `redis` and `postgres`. On Windows, uvicorn is given a selector event loop; its
default Proactor loop is rejected by psycopg's async driver.

### One process per container

Uvicorn can take a live FastAPI object (what `main.py` passes) or an import string such as
`app.main:app`. The string exists so a **new** process can import a fresh app; you cannot hand
a live in-memory graph to a child. `--reload` (restart on file change) and `--workers N`
(N processes behind one master) both need that string. `--reload` is a laptop convenience
and stays out of the entry point.

`--workers` is the classic one-VM pattern (Gunicorn-style workers on a single box). This
README's production shape is Kubernetes: **one app process per container, N Pods for
throughput**. Liveness and readiness probes, `SIGTERM`, memory limits, and HPA all assume
that. The same parallelism is **several small Pods** (about 1–2 cores each). The scheduler,
rolling deploys, and "this replica is sick" then match one process. Eight workers inside one
container look like **one** container to the kubelet: CPU and memory requests become a guess,
and a kill of the container kills every worker.

## Schema migrations

Alembic is a **separate entry point** from the HTTP process. It lives at the repo root
(`alembic.ini`, `alembic/`), builds its own sync engine from `POSTGRES__*`, and uses
`PostgresBase.metadata`. It never constructs `PostgresClient` or `LifecycleManager`. The DSN is
never stored in `alembic.ini`.

Apply:

```bash
uv run alembic upgrade head
```

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 04befa978a2d, create feature_flags
```

Create a revision after changing ORM mappings:

```bash
uv run alembic revision --autogenerate -m "add whatever"
```

Review the file under `alembic/versions/` before committing. Autogenerate is a draft: it will not
invent data backfills, constraint rewrites, or destructive drops you did not mean. Edit
`upgrade()` / `downgrade()` when production data needs a safer path.

Do not run Alembic from `main.py` or on replica startup.

## Container image

The [Dockerfile](Dockerfile) is a production-style image (multi-stage, non-root, frozen lockfile,
no `.env`). The virtualenv and Alembic files are owned by root; the runtime user cannot
rewrite them. It is **not** used by the default local loop. One image contains the application,
the Alembic CLI, and `alembic/versions/`.

```bash
docker build -t fastapi-polyrepo-template .
```

Default command starts the server only:

```bash
docker run --rm -p 8080:8080 --env-file .env fastapi-polyrepo-template
```

Override the command to migrate (inject the same `POSTGRES__*` as the app; use service DNS names
inside Compose/Kubernetes networks, not `127.0.0.1`):

```bash
docker run --rm --env-file .env fastapi-polyrepo-template alembic upgrade head
```

Do not chain `alembic upgrade head && app` in `CMD`. Replicas must not migrate.

## Production deploy

Treat schema as an explicit step that **gates** the application. Same image, two commands:

```
Same image
    ├── Job: alembic upgrade head     (run to completion; fail the rollout on error)
    └── Deployment / ReplicaSet: app  (start only after the Job succeeded)
```

Do not start app replicas until that Job has succeeded. This repository does not ship Helm or
Kubernetes YAML; the contract above is what a later chart should implement.

## Testing

```bash
uv run pytest
```

Three trees, one invocation. Layout under each tree mirrors `src/app/`. Docker Desktop must be running for integration and e2e;
`uv run pytest tests/unit` does not start containers.

```bash
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e
```

- **Unit** ([tests/unit/](tests/unit/README.md)): In-process. The service under test is real;
  Redis and Postgres are injected doubles (`AsyncMock`), so nothing binds a socket. Example:
  `FeatureFlagService` cache-aside reads in `tests/unit/services/feature_flag_service/`.
- **Integration** ([tests/integration/](tests/integration/README.md)): The same
  `FeatureFlagService` against throwaway Redis and PostgreSQL via Testcontainers.
- **End-to-end** ([tests/e2e/](tests/e2e/README.md)): HTTP through `LifecycleManager` against
  the same throwaway stores.

## Linting and type checking

```bash
uv run ruff format .
uv run ruff check .
uv run pyright
uv run lint-imports
```

[Ruff](https://docs.astral.sh/ruff/) both formats and lints: 100-column lines, double quotes, and a
broad rule set that includes Google-style docstring checks, import sorting, and a ban on `print`.
Formatting is the formatter's job alone — the quote and comma lint rules are deliberately left off
because they fight it.

[Pyright](https://microsoft.github.io/pyright/) runs in strict mode over `src`, `tests`, and `alembic`.

[Import Linter](https://import-linter.readthedocs.io/) enforces the one-directional stack: an
upward import, a cycle, or a new top-level package that has not been placed in the hierarchy all
fail the contract. So does a service or client that imports FastAPI.

All three are configured in `pyproject.toml`, and every rule exemption there carries a comment
explaining itself.

The same four commands run on `git commit` via [pre-commit](https://pre-commit.com/). Format in the
hook is `ruff format --check .`, so an unformatted tree fails the commit instead of rewriting it.
After `uv sync`, install the hook once:

```bash
uv run pre-commit install
```

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on pushes and pull requests to `main`:
ruff, pyright, import-linter, the full pytest suite (unit, integration, and e2e — GitHub-hosted
Ubuntu has Docker, so Testcontainers can start), and `docker build` with no push. There is no
deploy workflow: where an image goes and how Alembic runs in production are product decisions, not
template ones.

[`.github/workflows/audit.yml`](.github/workflows/audit.yml) runs `uv audit --locked` on those
same events and weekly, so a CVE published while `main` is idle still fails the Audit badge.
Dependabot ([`.github/dependabot.yml`](.github/dependabot.yml)) opens weekly PRs for the `uv`
lockfile and for GitHub Actions; outdated packages without a known CVE do not fail Audit.

## Authentication

This template does not ship authentication. The scheme is a product choice (JWT, Basic,
mTLS, or none). Many deployments never authenticate in-process: an API gateway or mesh
already did. Shipping one scheme would become the pattern every later change — including
AI-assisted ones — copies.

Identity is **request-scoped**. It is not a constructor dependency on a service.
The route takes claims or `SessionInfo` through FastAPI `Depends`, then passes
`user_id` (and whatever else the use case needs) into the service method. A service
that imports `Request` or takes `SessionInfo` in `__init__` is the bug this layout
exists to prevent.

Use `Depends`, not ASGI middleware. Kubernetes probes and `GET /metrics` stay
callable because they simply omit the dependency — [`k8s_probe_router`](src/app/routes/k8s_probe_router.py)
is already dependency-free.

Longer copies of the accessors live in [`src/app/state/README.md`](src/app/state/README.md).
If you later need a process-wide 401 before routing, see
[`src/app/middlewares/README.md`](src/app/middlewares/README.md).

### JWT Example

Verify the signature against the issuer's JWKS. Construct `JwtAuthService` and
`PyJWKClient` in `LifecycleManager`; the handler must not construct either.
Read `Authorization` on the `Request` (same as the session header). Do not use
module-level `HTTPBearer()`.

```python
async def require_access_token(
    request: Request,
    auth: Annotated[JwtAuthService, Depends(get_jwt_auth_service)],
) -> AccessTokenClaims:
    header = request.headers.get("Authorization")
    if header is None or not header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        return auth.verify(header.removeprefix("Bearer "))
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from None


@orders_router.get("/me", name="orders-router.me")
async def get_my_orders(
    claims: Annotated[AccessTokenClaims, Depends(require_access_token)],
    service: Annotated[OrdersService, Depends(get_orders_service)],
) -> list[Order]:
    return await service.list_for_user(user_id=claims.sub)
```

`JwtAuthService.verify` uses [PyJWT](https://pyjwt.readthedocs.io/en/stable/api.html).
Pass `algorithms` as a fixed list, never from the token's `alg` header.
`jwt.decode` returns `dict[str, Any]`. Do not log the raw token.

```python
def verify(self, token: str) -> AccessTokenClaims:
    signing_key: PyJWK = self._jwks.get_signing_key_from_jwt(token)
    payload: dict[str, Any] = jwt.decode(
        token,
        key=signing_key,
        algorithms=["RS256"],
        audience=self._audience,
        issuer=self._issuer,
    )
    return AccessTokenClaims.model_validate(payload)
```

### Session Example

A gateway that already authenticated the caller can send a session id on a trusted
internal header (`X-Session-ID`, a constant in `app_consts.py` like the other
headers). `SessionService` loads `SessionInfo` through the existing `RedisClient`.
Unknown or missing sessions are `401`.

```python
async def require_session(
    request: Request,
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> SessionInfo:
    session_id = request.headers.get(SESSION_ID_HEADER)
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    session = await sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return session


@orders_router.get("/me", name="orders-router.me")
async def get_my_orders(
    session: Annotated[SessionInfo, Depends(require_session)],
    service: Annotated[OrdersService, Depends(get_orders_service)],
) -> list[Order]:
    return await service.list_for_user(user_id=session.user_id)
```

`require_session` must not call `RedisClient`. `SessionService` is constructed in
`LifecycleManager` like `FeatureFlagService`, with an injected client and child logger.
