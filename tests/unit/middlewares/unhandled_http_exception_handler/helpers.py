"""Tiny FastAPI app that can boom or 404, with the production exception handler."""

from fastapi import FastAPI, HTTPException, status

from app.logger import LogManager
from app.middlewares import (
    CorrelationIdMiddleware,
    make_unhandled_http_exception_handler,
)


def build_unhandled_exception_app(log_manager: LogManager) -> FastAPI:
    """App with ``GET /boom``, ``GET /missing``, and ``GET /ok``.

    Mirrors production: ``Exception`` handler first, then correlation id.

    Args:
        log_manager: Manager whose ``uvicorn`` child the handler logs through.

    Returns:
        An application whose unhandled errors become a generic 500.
    """
    app = FastAPI()
    app.add_exception_handler(
        Exception,
        make_unhandled_http_exception_handler(log_manager.get_child_logger("uvicorn")),
    )

    async def boom() -> None:
        """Raise an unhandled error so the generic 500 path runs."""
        raise RuntimeError("boom")

    async def missing() -> None:
        """Raise a domain 404 that must not use the unhandled handler."""
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="gone")

    async def ok() -> dict[str, bool]:
        """Return a body the tests ignore.

        Returns:
            A trivial JSON payload.
        """
        return {"ok": True}

    app.add_api_route("/boom", boom)
    app.add_api_route("/missing", missing)
    app.add_api_route("/ok", ok)
    app.add_middleware(CorrelationIdMiddleware)
    return app
