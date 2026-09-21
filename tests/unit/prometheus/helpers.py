"""Tiny FastAPI app mirroring lifecycle's PrometheusManager wiring."""

from fastapi import FastAPI
from prometheus_client import CollectorRegistry

from app.config import PrometheusConfig
from app.middlewares import CorrelationIdMiddleware
from app.prometheus import (
    PrometheusManager,
    make_inbound_request_id_instrumentation,
)


def instrumented_app(
    registry: CollectorRegistry,
    config: PrometheusConfig | None = None,
) -> FastAPI:
    """App with ``GET /ping`` and ``GET /metrics`` on a private collector.

    Mirrors ``LifecycleManager``: construct ``PrometheusManager``, then
    ``add_http_instrumentation``, then ``add_middleware``, then correlation id,
    then ``add_metrics_router``. Secure headers are covered in
    ``tests/unit/middlewares/secure_headers`` and are not this suite's subject.

    Args:
        registry: Private collector so this test cannot collide with another.
        config: Gzip for the scrape path. Defaults to ``PrometheusConfig()``.

    Returns:
        An application with ``GET /ping`` and ``GET /metrics``.
    """
    app = FastAPI()

    async def ping() -> dict[str, bool]:
        """Return a body the tests ignore.

        Returns:
            A trivial JSON payload.
        """
        return {"ok": True}

    app.add_api_route("/ping", ping)

    prometheus = PrometheusManager(registry=registry)
    prometheus.add_http_instrumentation(
        make_inbound_request_id_instrumentation(prometheus.registry),
    )
    prometheus.add_middleware(app)
    app.add_middleware(CorrelationIdMiddleware)
    prometheus.add_metrics_router(
        app,
        config if config is not None else PrometheusConfig(),
    )
    return app
