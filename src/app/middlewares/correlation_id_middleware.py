"""ASGI middleware that binds a correlation id for the lifetime of a request."""

from typing import Final
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import CORRELATION_ID_HEADER, CORRELATION_ID_STATE_KEY, REQUEST_ID_HEADER


class CorrelationIdMiddleware:
    """Attach a correlation id to the request, the response, and every log line.

    Incoming ``X-Request-ID`` wins when it is non-empty after stripping; otherwise
    ``X-Correlation-ID`` is used; otherwise a UUID4 is generated. The id that was
    chosen is always returned as ``X-Request-ID``.

    The id is bound with ``structlog.contextvars.bound_contextvars``, which
    ``LogManager`` already merges into every record via ``merge_contextvars``.
    It is also stored on ``scope["state"]`` under ``CORRELATION_ID_STATE_KEY`` so
    the unhandled HTTP exception handler can still read it after this context
    manager exits.
    No extra ``ContextVar`` is declared: that would duplicate structlog's store
    and drift out of the processor chain. The context manager unbinds on the
    way out so the next task on this event loop cannot inherit the id.

    This is a raw ASGI wrapper rather than ``BaseHTTPMiddleware``. Starlette
    documents that the latter can swallow the request body on streamed
    requests; a correlation id must not do that.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap ``app``.

        Args:
            app: The next ASGI application in the stack. The composition root
                passes this in via ``add_middleware``; this class never installs
                itself.
        """
        self._app: Final = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind the id for HTTP requests; pass other scopes through unchanged.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable. HTTP responses are wrapped so the chosen
                id is written to ``X-Request-ID``.
        """
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        correlation_id = _correlation_id_from_headers(Headers(scope=scope))
        scope.setdefault("state", {})[CORRELATION_ID_STATE_KEY] = correlation_id

        async def send_with_request_id(message: Message) -> None:
            """Echo the correlation id on the HTTP response start.

            Args:
                message: An ASGI event. Only ``http.response.start`` is altered.
            """
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = correlation_id
            await send(message)

        with structlog.contextvars.bound_contextvars(correlation_id=correlation_id):
            await self._app(scope, receive, send_with_request_id)


def _correlation_id_from_headers(headers: Headers) -> str:
    """Pick the inbound id, preferring ``X-Request-ID``.

    Args:
        headers: Request headers. Lookup is case-insensitive.

    Returns:
        A stripped inbound value, or a new UUID4 when neither header is usable.
    """
    for name in (REQUEST_ID_HEADER, CORRELATION_ID_HEADER):
        value = headers.get(name, "").strip()
        if value:
            return value
    return str(uuid4())
