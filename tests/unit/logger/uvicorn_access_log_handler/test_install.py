"""Install on the process ``uvicorn.access`` logger lets INFO records through."""

import logging
from io import BytesIO

from app.logger import LogManager, install_uvicorn_access_logging
from tests.unit.logger.log_manager.helpers import read_records


def test_install_forwards_info_from_the_stdlib_logger(
    log_manager: LogManager,
    sink: BytesIO,
) -> None:
    """Root WARNING must not swallow uvicorn access INFO after install.

    ``log_config=None`` never sets this logger's level. Install must, or
    per-request access lines never reach the structured handler.
    """
    stdlib = logging.getLogger("uvicorn.access")
    previous_handlers = list(stdlib.handlers)
    previous_level = stdlib.level
    previous_propagate = stdlib.propagate
    try:
        install_uvicorn_access_logging(log_manager.get_child_logger("uvicorn.access"))
        stdlib.info(
            '%s - "%s %s HTTP/%s" %d',
            "127.0.0.1:54321",
            "GET",
            "/api/v1/feature-flags/dark_mode",
            "1.1",
            200,
        )

        (line,) = read_records(sink)
        assert line["context"] == "uvicorn.access"
        assert line["level"] == "info"
        assert line["msg"] == (
            '127.0.0.1:54321 - "GET /api/v1/feature-flags/dark_mode HTTP/1.1" 200'
        )
    finally:
        stdlib.handlers = previous_handlers
        stdlib.setLevel(previous_level)
        stdlib.propagate = previous_propagate
