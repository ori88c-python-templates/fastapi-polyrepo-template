# state

Typed application state and the accessors that recover it from FastAPI's untyped bag.

## Belongs here

- `AppState`, `AppClients`, and `AppServices`: the frozen container the composition
  root fills once and every request reads.
- The getters that take a `Request` or `FastAPI` app and return a real type.
  Bag accessors (`get_app_state`, `get_app_services`) and per-service `Depends`
  helpers (`get_feature_flag_service`) all live in `app_state_getters.py`. Name
  later service getters `get_<use_case>_service`.

Callers outside this package import from [`__init__.py`](__init__.py):
`from app.state import AppState, get_feature_flag_service`. Modules inside it
still import siblings by module path (`from app.state.app_state import AppState`);
a getter importing `from app.state import AppState` would cycle.

## Does not belong here

- Constructing clients or services. `LifecycleManager` is the composition root; this
  package only types and retrieves what that root already built.
- Business logic or HTTP handlers.

## Why a package of its own

Route handlers inject dependencies through FastAPI `Depends`. Those callables have to
import the getters. The getters cannot live in `lifecycle/`: that package sits *above*
`routes/`, so a router importing it would be an upward import and a cycle once the
composition root imported the router.

This package sits below the HTTP layer and above `services/`, which is the one place
that can know FastAPI, `AppServices`, and `AppClients` without either layering
violation. `get_app_state_from_app` remains the only cast in the codebase.

## Request-scoped identity (when you add auth)

Auth is not shipped. When a clone adds it, the accessors still live here, next to
`get_feature_flag_service`. They call `get_app_services()`, never
`get_app_state().clients`. Identity is per request: the route `Depends` on claims or
`SessionInfo` and passes `user_id` into the service method. Do not put `SessionInfo` on
a service `__init__`.

Name getters `get_jwt_auth_service` / `get_session_service`. The `require_*`
callables are also `Depends` targets; they belong in this package because they
need `Request` and `AppServices`.

`JwtAuthService` / `SessionService` are constructed in `LifecycleManager`. Probes and
`GET /metrics` omit these dependencies. See the root README Authentication section.

