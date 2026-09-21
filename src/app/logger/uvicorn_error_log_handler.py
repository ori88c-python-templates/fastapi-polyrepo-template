"""Bridge ``uvicorn.error`` into a structured ``LogManager`` child.

Uvicorn's ``uvicorn.error`` logger is not error-only: startup, shutdown, warnings,
and failures all go through it. Per-request lines are ``uvicorn.access`` and are
bridged separately.
"""

import logging
from typing import Final

from structlog.typing import FilteringBoundLogger

from app.logger.uvicorn_asgi_exception_filter import UvicornAsgiExceptionFilter
from app.logger.uvicorn_log_handler import UvicornLogHandler

_UVICORN_ERROR_LOGGER: Final = "uvicorn.error"


def install_uvicorn_error_logging(logger: FilteringBoundLogger) -> None:
    """Attach the ASGI filter and structured handler to ``uvicorn.error``.

    ``propagate`` is turned off so root / lastResort does not also print the
    same line as unstructured text. The ASGI exception filter stays so a
    FastAPI-handled HTTP 500 is not indexed twice.

    ``log_config=None`` skips uvicorn's ``dictConfig`` that would set this
    logger to INFO. Without an explicit level the effective level is the root
    WARNING, so startup INFO lines never reach the handler.

    Args:
        logger: Child logger named ``uvicorn``. Closed over by the handler.
    """
    uvicorn_error = logging.getLogger(_UVICORN_ERROR_LOGGER)
    uvicorn_error.addFilter(UvicornAsgiExceptionFilter())
    uvicorn_error.addHandler(UvicornLogHandler(logger))
    uvicorn_error.setLevel(logging.DEBUG)
    uvicorn_error.propagate = False
