"""Configuration for structured logging."""

from enum import StrEnum

from pydantic import BaseModel


class LogLevel(StrEnum):
    """Log levels accepted by structlog.

    These are exactly structlog's canonical level names, i.e. the values of
    ``structlog._log_levels.LEVEL_TO_NAME``. structlog's ``NAME_TO_LEVEL`` map also
    accepts ``warn``, ``exception`` and ``notset``, but those are aliases rather than
    distinct levels and are deliberately not offered here.

    The enum is declared without importing structlog so that the config package stays
    free of runtime dependencies on the logging implementation.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LoggerConfig(BaseModel):
    """Logging configuration.

    ``LogManager`` applies ``MIN_LOG_LEVEL`` only. Whether uvicorn access lines
    are installed is a composition-root decision in ``main`` /
    ``LifecycleManager``.

    Attributes:
        MIN_LOG_LEVEL: Lowest severity that will be emitted. Records below this level
            are discarded before any processor runs.
        ENABLE_UVICORN_ACCESS_LOGS: When true (uvicorn's default), ``uvicorn.access``
            is bridged into a ``context="uvicorn.access"`` child as JSON. When
            false, ``uvicorn.run(..., access_log=False)`` and no access lines
            are emitted.
    """

    MIN_LOG_LEVEL: LogLevel = LogLevel.INFO
    ENABLE_UVICORN_ACCESS_LOGS: bool = True
