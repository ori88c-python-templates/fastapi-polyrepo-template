"""Typed manager over the untyped prometheus-fastapi-instrumentator library."""

from collections.abc import Callable, Sequence
from typing import Any, Final

from fastapi import FastAPI
from prometheus_client import REGISTRY, CollectorRegistry
from prometheus_fastapi_instrumentator import (  # type: ignore[import-untyped]
    Instrumentator,
    metrics,
)

from app.config import LIVEZ_ENDPOINT, METRICS_ENDPOINT, READYZ_ENDPOINT, PrometheusConfig

_EXCLUDED_HANDLERS: Final = (METRICS_ENDPOINT, LIVEZ_ENDPOINT, READYZ_ENDPOINT)


class PrometheusManager:
    """Owns the scrape registry, HTTP default metrics, and how they attach to FastAPI.

    The wrapped library has no type stubs. This class is the boundary: Lifecycle and
    tests never call ``Instrumentator`` themselves.

    Default HTTP series (request count, latency) are installed in ``__init__``.
    Product HTTP callbacks are registered by the composition root so this class
    does not become a catalog of every series.
    """

    def __init__(
        self,
        *,
        excluded_handlers: Sequence[str] = _EXCLUDED_HANDLERS,
        registry: CollectorRegistry | None = None,
    ) -> None:
        """Build the instrumentator with default HTTP metrics only.

        ``Instrumentator.add`` disables the library's implicit defaults, so
        ``metrics.default`` is installed here.

        Args:
            excluded_handlers: Paths omitted from HTTP series. Probes and
                ``/metrics`` itself are excluded by default so scrape and kubelet
                traffic do not inflate request counts.
            registry: Collector to register with. ``None`` uses the process-wide
                default. Tests pass a private registry.
        """
        chosen_registry: Final = registry if registry is not None else REGISTRY
        instrumentator: Final[Any] = Instrumentator(
            excluded_handlers=list(excluded_handlers),
            registry=chosen_registry,
        )
        default_metrics: Any = metrics.default(  # pyright: ignore[reportUnknownMemberType]
            registry=chosen_registry,
        )
        instrumentator.add(default_metrics)
        self._instrumentator: Final[Any] = instrumentator
        self._registry: Final[CollectorRegistry] = chosen_registry
        self._middleware_installed: bool = False

    @property
    def registry(self) -> CollectorRegistry:
        """The collector ``/metrics`` scrapes and that services must share.

        Returns:
            The registry this manager was constructed with.
        """
        return self._registry

    def add_http_instrumentation(self, *callbacks: Callable[..., object]) -> None:
        """Register extra HTTP instrumentation callbacks.

        Must run before ``add_middleware``: the library snapshots the callback
        list when middleware is installed.

        Args:
            callbacks: Callables invoked on each instrumented request.

        Raises:
            RuntimeError: If Prometheus middleware is already on the app.
        """
        if self._middleware_installed:
            raise RuntimeError(
                "HTTP instrumentation callbacks must be registered before "
                "add_middleware: the middleware already captured the callback list."
            )
        self._instrumentator.add(*callbacks)

    def add_middleware(self, app: FastAPI) -> None:
        """Install Prometheus ASGI middleware on ``app``.

        Args:
            app: The application to wrap. Must run inside
                ``_add_middlewares_in_order`` so this layer sits innermost.

        Raises:
            RuntimeError: If this manager has already installed middleware.
        """
        if self._middleware_installed:
            raise RuntimeError("Prometheus middleware is already installed.")
        self._instrumentator.instrument(app)
        self._middleware_installed = True

    def add_metrics_router(self, app: FastAPI, config: PrometheusConfig) -> None:
        """Mount ``GET /metrics`` on ``app``.

        The path is always omitted from OpenAPI: Prometheus text is a scrape
        contract, not product API. Gzip still comes from ``config``.

        Args:
            app: The application to mount on. Call from ``_register_routers``.
            config: Gzip for the scrape body. The path is ``METRICS_ENDPOINT``.
        """
        self._instrumentator.expose(
            app,
            endpoint=METRICS_ENDPOINT,
            include_in_schema=False,
            should_gzip=config.SHOULD_GZIP,
        )
