"""Drop uvicorn's unstructured duplicate of an HTTP 500 we already logged.

Starlette's ``ServerErrorMiddleware`` always re-raises after sending the generic
500 so the server can log. Uvicorn then emits ``uvicorn.error`` with
``Exception in ASGI application`` and a traceback on stderr. This app has
already written a structured JSON line (``context=uvicorn``, ``correlation_id``).
Without the filter, observability tools index two events for one failure: JSON
that can be queried, and a raw traceback that cannot. Dropping the uvicorn
record is how Groundcover and Grafana see a single event.
"""

import logging
from typing import Final

_UVICORN_ASGI_EXCEPTION_PREFIX: Final = "Exception in ASGI application"


class UvicornAsgiExceptionFilter(logging.Filter):
    """Keep every ``uvicorn.error`` record except the ASGI exception traceback."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Drop uvicorn's duplicate of a handled HTTP 500.

        Uvicorn 0.52 formats the message with a trailing newline in
        ``HttpToolsProtocol.run_asgi``. ``startswith`` survives that suffix.

        Args:
            record: A ``uvicorn.error`` record.

        Returns:
            False when this is uvicorn's unstructured ASGI exception log.
        """
        return not record.getMessage().startswith(_UVICORN_ASGI_EXCEPTION_PREFIX)
