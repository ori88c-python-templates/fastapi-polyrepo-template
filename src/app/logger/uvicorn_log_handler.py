"""Rewrite a uvicorn stdlib ``LogRecord`` through a closed-over child logger."""

import logging
from typing import Final

from structlog.typing import FilteringBoundLogger


def _structlog_method_for_level(levelno: int) -> str:
    """Map a stdlib ``levelno`` to a ``FilteringBoundLogger`` method name.

    Uvicorn's TRACE (5) is below ``DEBUG`` and becomes ``debug``.

    Args:
        levelno: ``LogRecord.levelno``.

    Returns:
        One of ``debug``, ``info``, ``warning``, ``error``, ``critical``.
    """
    if levelno >= logging.CRITICAL:
        return "critical"
    if levelno >= logging.ERROR:
        return "error"
    if levelno >= logging.WARNING:
        return "warning"
    if levelno >= logging.INFO:
        return "info"
    return "debug"


class UvicornLogHandler(logging.Handler):
    """Forward uvicorn's ``uvicorn.error`` or ``uvicorn.access`` records as JSON."""

    def __init__(self, logger: FilteringBoundLogger) -> None:
        """Keep the child logger this handler emits through.

        Args:
            logger: Child named ``uvicorn`` or ``uvicorn.access``. Closed over so
                this package does not reach for a global ``LogManager``.
        """
        super().__init__()
        self._logger: Final = logger

    def emit(self, record: logging.LogRecord) -> None:
        """Forward ``record`` at the matching structlog level.

        The event string is uvicorn's sentence (``record.getMessage()``), not a
        dotted app event. ``exc_info`` is passed through when the record has one.

        Args:
            record: A ``uvicorn.error`` or ``uvicorn.access`` record.
        """
        try:
            message = record.getMessage()
            extra: dict[str, object] = {}
            if record.exc_info:
                extra["exc_info"] = record.exc_info
            match _structlog_method_for_level(record.levelno):
                case "critical":
                    self._logger.critical(message, **extra)
                case "error":
                    self._logger.error(message, **extra)
                case "warning":
                    self._logger.warning(message, **extra)
                case "info":
                    self._logger.info(message, **extra)
                case _:
                    self._logger.debug(message, **extra)
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)
