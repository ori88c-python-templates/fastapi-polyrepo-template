"""Log unhandled HTTP exceptions as structured JSON without leaking the body."""

from collections.abc import Awaitable, Callable
from typing import Final

from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from structlog.typing import FilteringBoundLogger

from app.config import CORRELATION_ID_STATE_KEY, REQUEST_ID_HEADER

_UNHANDLED_HTTP_EVENT: Final = "http.unhandled_exception"
_GENERIC_500_BODY: Final = "Internal Server Error"


def make_unhandled_http_exception_handler(
    logger: FilteringBoundLogger,
) -> Callable[[Request, Exception], Awaitable[Response]]:
    """Build FastAPI's ``Exception`` handler: log, then return a generic 500.

    Starlette's ``ServerErrorMiddleware`` calls this outside user middleware, after
    ``correlation_id`` has been unbound from contextvars. The id is read from
    ``request.state`` (set by ``CorrelationIdMiddleware``) and passed as a kwarg.

    Args:
        logger: Child logger named ``uvicorn``. Closed over so this package does
            not reach for a global ``LogManager``.

    Returns:
        An async callable for ``app.add_exception_handler(Exception, ...)``.
    """

    async def handle_unhandled_http_exception(request: Request, exc: Exception) -> Response:
        """Log ``exc`` and return Starlette's generic 500 body.

        Args:
            request: The request that failed. ``CORRELATION_ID_STATE_KEY`` on
                ``request.state`` is set by ``CorrelationIdMiddleware``.
            exc: The unhandled exception. Its text is logged, never returned.

        Returns:
            ``500 Internal Server Error`` as ``text/plain``.
        """
        correlation_id = getattr(request.state, CORRELATION_ID_STATE_KEY, None)
        if correlation_id is None:
            logger.error(_UNHANDLED_HTTP_EVENT, exc_info=exc)
        else:
            logger.error(
                _UNHANDLED_HTTP_EVENT,
                exc_info=exc,
                correlation_id=correlation_id,
            )
        headers: dict[str, str] = {}
        if correlation_id:
            headers[REQUEST_ID_HEADER] = str(correlation_id)
        return PlainTextResponse(_GENERIC_500_BODY, status_code=500, headers=headers)

    return handle_unhandled_http_exception
