"""Bridge ``uvicorn.access`` into a structured ``LogManager`` child.

Uvicorn emits one INFO record per finished response on ``uvicorn.access``, on
``http.response.start`` — while ``CorrelationIdMiddleware`` still holds
``bound_contextvars``, so ``correlation_id`` is merged without reading
``request.state``.
"""

import logging
from typing import Final

from structlog.typing import FilteringBoundLogger

from app.logger.uvicorn_log_handler import UvicornLogHandler

_UVICORN_ACCESS_LOGGER: Final = "uvicorn.access"


def install_uvicorn_access_logging(logger: FilteringBoundLogger) -> None:
    """Attach the structured handler to ``uvicorn.access``.

    ``propagate`` is turned off so root / lastResort does not also print the
    same line as unstructured text. Uvicorn only writes access lines when this
    logger ``hasHandlers()``, so the handler must be installed before
    ``uvicorn.run``.

    ``log_config=None`` skips uvicorn's ``dictConfig`` that would set this
    logger to INFO. Without an explicit level the effective level is the root
    WARNING, so access INFO lines never reach the handler.

    Args:
        logger: Child logger named ``uvicorn.access``. Closed over by the handler.
    """
    uvicorn_access = logging.getLogger(_UVICORN_ACCESS_LOGGER)
    uvicorn_access.addHandler(UvicornLogHandler(logger))
    uvicorn_access.setLevel(logging.DEBUG)
    uvicorn_access.propagate = False
