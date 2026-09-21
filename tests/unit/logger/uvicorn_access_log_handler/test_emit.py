"""Forward uvicorn.access records through a LogManager child named ``uvicorn.access``."""

import logging
from io import BytesIO

from app.logger import LogManager, UvicornLogHandler
from tests.unit.logger.log_manager.helpers import read_records


def test_info_record_is_structured_json(log_manager: LogManager, sink: BytesIO) -> None:
    """Uvicorn's access format string becomes JSON with the interpolated sentence."""
    handler = UvicornLogHandler(log_manager.get_child_logger("uvicorn.access"))
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:54321", "GET", "/api/v1/feature-flags/dark_mode", "1.1", 200),
        exc_info=None,
    )

    handler.emit(record)

    (line,) = read_records(sink)
    assert line["context"] == "uvicorn.access"
    assert line["level"] == "info"
    assert line["msg"] == '127.0.0.1:54321 - "GET /api/v1/feature-flags/dark_mode HTTP/1.1" 200'
