"""Build a tiny FastAPI app that logs once per request through a given manager."""

from fastapi import FastAPI

from app.logger import LogManager
from app.middlewares.correlation_id_middleware import CorrelationIdMiddleware


def build_logging_app(log_manager: LogManager) -> FastAPI:
    """Mount a single ``/ping`` handler behind ``CorrelationIdMiddleware``.

    Args:
        log_manager: Manager the handler logs through. Tests inspect its stream
            for the bound ``correlation_id``.

    Returns:
        An application whose only interesting behaviour is one log line per GET.
    """
    app = FastAPI()

    async def ping() -> dict[str, bool]:
        """Emit one record so tests can read the bound correlation id.

        Returns:
            A body the tests ignore; the log line is the assertion surface.
        """
        log_manager.get_child_logger("ping").info("ping.ok")
        return {"ok": True}

    app.add_api_route("/ping", ping)
    app.add_middleware(CorrelationIdMiddleware)
    return app
