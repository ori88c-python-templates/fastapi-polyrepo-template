"""Install on the process ``uvicorn.error`` logger lets INFO records through."""

import logging
from io import BytesIO

from app.logger import LogManager, install_uvicorn_error_logging
from tests.unit.logger.log_manager.helpers import read_records


def test_install_forwards_info_from_the_stdlib_logger(
    log_manager: LogManager,
    sink: BytesIO,
) -> None:
    """Root WARNING must not swallow uvicorn startup INFO after install.

    ``log_config=None`` never sets this logger's level. Install must, or
    ``Started server process`` never reaches the structured handler.
    """
    stdlib = logging.getLogger("uvicorn.error")
    previous_handlers = list(stdlib.handlers)
    previous_filters = list(stdlib.filters)
    previous_level = stdlib.level
    previous_propagate = stdlib.propagate
    try:
        install_uvicorn_error_logging(log_manager.get_child_logger("uvicorn"))
        stdlib.info("Started server process [%s]", 1234)

        (line,) = read_records(sink)
        assert line["context"] == "uvicorn"
        assert line["level"] == "info"
        assert line["msg"] == "Started server process [1234]"
    finally:
        stdlib.handlers = previous_handlers
        stdlib.filters = previous_filters
        stdlib.setLevel(previous_level)
        stdlib.propagate = previous_propagate
