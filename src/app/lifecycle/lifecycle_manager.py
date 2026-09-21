"""Construction, startup and shutdown of the FastAPI application."""

import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI

from app.clients import PostgresClient, RedisClient
from app.config import REDOC_ENDPOINT, SWAGGER_DOCS_ENDPOINT, AppConfig
from app.distribution import installed_app_version
from app.logger import (
    LogManager,
    make_asyncio_exception_handler,
    make_sys_excepthook,
)
from app.logger import (
    install_uvicorn_access_logging as _install_uvicorn_access_logging,
)
from app.logger import (
    install_uvicorn_error_logging as _install_uvicorn_error_logging,
)
from app.metrics import FeatureFlagMetrics
from app.middlewares import (
    CorrelationIdMiddleware,
    SecureASGIMiddleware,
    default_secure_headers,
    make_unhandled_http_exception_handler,
)
from app.prometheus import (
    PrometheusManager,
    make_inbound_request_id_instrumentation,
)
from app.routes import feature_flag_router, k8s_probe_router
from app.services import FeatureFlagService
from app.state import (
    APP_STATE_ATTRIBUTE,
    AppClients,
    AppServices,
    AppState,
    get_app_state_from_app,
)

_LIFECYCLE_LOGGER_NAME: Final = "LifecycleManager"
_REDIS_LOGGER_NAME: Final = "RedisClient"
_POSTGRES_LOGGER_NAME: Final = "PostgresClient"
_FEATURE_FLAG_LOGGER_NAME: Final = "FeatureFlagService"
_UVICORN_LOGGER_NAME: Final = "uvicorn"
_UVICORN_ACCESS_LOGGER_NAME: Final = "uvicorn.access"
_ASYNCIO_LOGGER_NAME: Final = "asyncio"
_SYS_EXCEPTHOOK_LOGGER_NAME: Final = "sys.excepthook"
_OPENAPI_TITLE: Final = "FastAPI Polyrepo Template"
_OPENAPI_DESCRIPTION: Final = "Read and update named feature flags."


class LifecycleManager:
    """Builds the application and owns the order its resources start and stop in.

    This is the composition root: the one place that constructs dependencies and hands
    them to each other. Nothing else in the codebase calls a constructor for a client,
    a service or a logger, which is what keeps the rest of the app free of global state.

    A class rather than a set of functions because every step wants the same two things,
    the configuration and a logger, and threading both through six function signatures
    is noise. Built once, in ``main``.
    """

    def __init__(self, app_config: AppConfig) -> None:
        """Prepare the manager and the logging every later step reports through.

        The ``LogManager`` is built here rather than during ``create_app`` because it is
        the one dependency the manager itself needs: it has to be able to log the
        construction of everything else, including the failures.

        Args:
            app_config: Fully validated configuration, built by the caller so that a bad
                environment fails before anything is constructed.
        """
        self._app_config: Final = app_config
        self._app_version: Final = installed_app_version()
        self._log_manager: Final = LogManager(
            app_config.logger,
            env=app_config.ENV,
            app_version=self._app_version,
        )
        self._logger: Final = self._log_manager.get_child_logger(_LIFECYCLE_LOGGER_NAME)
        self._prometheus: Final = PrometheusManager()
        self._prometheus.add_http_instrumentation(
            make_inbound_request_id_instrumentation(self._prometheus.registry),
        )

    def create_app(self) -> FastAPI:
        """Build the application and everything it depends on.

        The state is attached before the application is returned, so it is in place well
        before the server runs the lifespan and long before the first request.

        Returns:
            An application ready to be served, with its routes and middleware registered
            and its startup and shutdown hooks installed.
        """
        self._logger.info("lifecycle.app.creating", env=self._app_config.ENV.value)

        app_state = self._build_app_state()
        app = FastAPI(
            title=_OPENAPI_TITLE,
            version=self._app_version,
            description=_OPENAPI_DESCRIPTION,
            docs_url=SWAGGER_DOCS_ENDPOINT,
            redoc_url=REDOC_ENDPOINT,
            lifespan=self._lifespan,
        )
        setattr(app.state, APP_STATE_ATTRIBUTE, app_state)

        app.add_exception_handler(
            Exception,
            make_unhandled_http_exception_handler(
                self._log_manager.get_child_logger(_UVICORN_LOGGER_NAME),
            ),
        )
        self._add_middlewares_in_order(app)
        self._register_routers(app)

        return app

    def install_sys_excepthook(self) -> None:
        """Replace ``sys.excepthook`` with a child logger named ``sys.excepthook``.

        Called from ``main`` so tests that only ``create_app`` do not take over
        the process hook. ``KeyboardInterrupt`` and ``SystemExit`` still use the
        interpreter default.
        """
        sys.excepthook = make_sys_excepthook(
            self._log_manager.get_child_logger(_SYS_EXCEPTHOOK_LOGGER_NAME),
        )

    def install_uvicorn_error_logging(self) -> None:
        """Bridge ``uvicorn.error`` into a child logger named ``uvicorn``.

        Called from ``main`` so tests that only ``create_app`` do not change
        process logging. Attaches the ASGI exception filter and a handler on
        the same child the HTTP 500 hook uses.
        """
        _install_uvicorn_error_logging(
            self._log_manager.get_child_logger(_UVICORN_LOGGER_NAME),
        )

    def install_uvicorn_access_logging(self) -> None:
        """Bridge ``uvicorn.access`` into a child logger named ``uvicorn.access``.

        Called from ``main`` so tests that only ``create_app`` do not change
        process logging. No-op when ``ENABLE_UVICORN_ACCESS_LOGS`` is false;
        ``main`` still passes that flag as ``access_log`` so uvicorn does not
        keep an empty logger that would print via lastResort.
        """
        if not self._app_config.logger.ENABLE_UVICORN_ACCESS_LOGS:
            return
        _install_uvicorn_access_logging(
            self._log_manager.get_child_logger(_UVICORN_ACCESS_LOGGER_NAME),
        )

    def _build_app_state(self) -> AppState:
        """Construct every long-lived object, in dependency order.

        The ``LogManager`` is already built. Clients are constructed here but not
        connected: there is no event loop yet. ``FeatureFlagService`` has no
        connection of its own, so it is ready as soon as it has the clients.

        Returns:
            The assembled state, with clients unopened until topological init.
        """
        self._logger.info("lifecycle.app_state.building")

        redis_client = RedisClient(
            self._app_config.redis,
            self._log_manager.get_child_logger(_REDIS_LOGGER_NAME),
        )
        postgres_client = PostgresClient(
            self._app_config.postgres,
            self._log_manager.get_child_logger(_POSTGRES_LOGGER_NAME),
        )
        feature_flag_service = FeatureFlagService(
            postgres_client,
            redis_client,
            self._app_config.feature_flag,
            self._log_manager.get_child_logger(_FEATURE_FLAG_LOGGER_NAME),
            FeatureFlagMetrics(registry=self._prometheus.registry),
        )

        return AppState(
            clients=AppClients(redis=redis_client, postgres=postgres_client),
            services=AppServices(feature_flag=feature_flag_service),
            log_manager=self._log_manager,
        )

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI) -> AsyncGenerator[None]:
        """Run resource startup before serving and teardown after.

        Installs the asyncio unhandled-exception hook on the running loop for
        the lifetime of this context, and restores the previous handler after
        teardown so ``stop()`` failures still get structured ``asyncio`` logs.

        Args:
            app: The application being started. Its state was attached by ``create_app``.

        Yields:
            Control to the server for as long as it is serving requests.
        """
        app_state = get_app_state_from_app(app)
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(
            make_asyncio_exception_handler(
                self._log_manager.get_child_logger(_ASYNCIO_LOGGER_NAME),
            )
        )
        try:
            await self._init_by_topological_order(app_state)
            try:
                yield
            finally:
                # A crash while serving still has to release connections, so teardown
                # belongs in `finally` rather than merely after the yield.
                await self._teardown_by_reverse_topological_order(app_state)
        finally:
            loop.set_exception_handler(previous_handler)

    async def _init_by_topological_order(self, app_state: AppState) -> None:
        """Open every resource that needs an event loop, dependencies first.

        Connection pools cannot be opened in ``_build_app_state`` because there is no
        running event loop yet, so construction and connection are deliberately separate
        steps. Redis and PostgreSQL do not depend on each other; Redis is started
        first to match the field order on ``AppClients``.

        Args:
            app_state: The state whose clients are being started.
        """
        self._logger.info("lifecycle.resources.initializing")

        await app_state.clients.redis.start()
        await app_state.clients.postgres.start()

    async def _teardown_by_reverse_topological_order(self, app_state: AppState) -> None:
        """Release every resource, in the exact reverse of the startup order.

        Reverse order is what makes shutdown graceful: a resource is only closed once
        everything that might still call it is already gone.

        The log manager is flushed last for the same reason. It is what everything else
        logs through, so draining it earlier would discard the records written while the
        remaining resources shut down.

        Args:
            app_state: The state being torn down.
        """
        self._logger.info("lifecycle.resources.tearing_down")

        try:
            await app_state.clients.postgres.stop()
        finally:
            try:
                await app_state.clients.redis.stop()
            finally:
                app_state.log_manager.flush()

    def _add_middlewares_in_order(self, app: FastAPI) -> None:
        """Register middleware, outermost last.

        Starlette wraps middleware in reverse registration order, so the last
        ``add_middleware`` call is the outermost: it sees the request first and the
        response last. Registration in this method is therefore:

        1. ``PrometheusManager.add_middleware(app)`` — Prometheus, innermost of
           the three. It measures the application. Header middleware is not a
           useful slice of latency, and keeping it inside correlation id means
           ``/metrics`` still receives ``X-Request-ID``.
        2. ``SecureASGIMiddleware`` — default security headers on every HTTP
           response, including probes, 404s, and ``/metrics``.
        3. ``CorrelationIdMiddleware`` — outermost, so every inner log line picks
           up ``correlation_id`` and every response carries ``X-Request-ID``.

        ``add_metrics_router`` is not called here: it mounts a router, not
        middleware.

        Third-party ``instrument(app)`` / ``setup(app)`` helpers often call
        ``app.add_middleware`` themselves. They belong in this method, in the
        intended slot, not after ``create_app()`` returns. Wrapping the app object
        in ``main`` (``app = SomeASGIWrapper(app)``) is outside FastAPI's stack
        entirely.

        Args:
            app: The application to register middleware on.
        """
        self._logger.info("lifecycle.middlewares.registering")

        self._prometheus.add_middleware(app)
        app.add_middleware(SecureASGIMiddleware, secure=default_secure_headers())
        app.add_middleware(CorrelationIdMiddleware)

    def _register_routers(self, app: FastAPI) -> None:
        """Mount every router onto the application.

        One router per use case, each owning its own prefix. The probe router is the
        exception and takes no prefix, since kubelet's configuration must not change
        when the API is versioned. It is omitted from OpenAPI in staging and
        production: kubelet is the only caller. ``/metrics`` is the same kind of
        unprefixed path, so ``add_metrics_router`` lives here next to the other
        routers rather than inside middleware registration. It is omitted from
        OpenAPI in every environment.

        Args:
            app: The application to mount routers on.
        """
        self._logger.info("lifecycle.routers.registering")

        app.include_router(
            k8s_probe_router,
            include_in_schema=self._app_config.ENV.include_probes_in_schema(),
        )
        app.include_router(feature_flag_router)
        self._prometheus.add_metrics_router(app, self._app_config.prometheus)
