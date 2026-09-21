"""Process entry point."""

import asyncio
import sys

import uvicorn

from app.config import AppConfig
from app.lifecycle import LifecycleManager


def make_selector_event_loop() -> asyncio.AbstractEventLoop:
    """Build a selector loop so psycopg async can run on Windows.

    Uvicorn's default Windows loop is ``ProactorEventLoop``, which psycopg
    refuses. Passed as ``loop=`` only on ``win32``.
    """
    return asyncio.SelectorEventLoop()


def main() -> None:
    """Load configuration, install process hooks, build the app, and serve it.

    Configuration is read first and separately so that an invalid environment fails
    here, before a single resource is constructed. The sys.excepthook and uvicorn
    bridges are process-wide, so they are installed here rather than inside
    ``create_app``. ``log_config=None`` keeps uvicorn from wiping those handlers
    with its default ``dictConfig``. ``access_log`` follows
    ``LOGGER__ENABLE_UVICORN_ACCESS_LOGS`` so uvicorn does not clear a handler we
    just attached, and so a disabled flag emits no access lines at all.
    """
    # AppConfig reads every field from the environment, but `redis` and `postgres` have
    # no defaults, so the type checker sees an incomplete call it has no way to know is
    # satisfied at runtime.
    app_config = AppConfig()  # pyright: ignore[reportCallIssue]
    lifecycle = LifecycleManager(app_config)
    lifecycle.install_sys_excepthook()
    lifecycle.install_uvicorn_error_logging()
    lifecycle.install_uvicorn_access_logging()
    app = lifecycle.create_app()

    uvicorn.run(
        app,
        host=app_config.server.HOST,
        port=app_config.server.PORT,
        log_config=None,
        access_log=app_config.logger.ENABLE_UVICORN_ACCESS_LOGS,
        loop="app.main:make_selector_event_loop" if sys.platform == "win32" else "auto",
    )


if __name__ == "__main__":
    main()
