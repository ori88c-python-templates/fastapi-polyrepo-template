"""Forward uvicorn.error records through a LogManager child named ``uvicorn``."""

import logging
import sys
from io import BytesIO

from app.logger import LogManager, UvicornLogHandler
from tests.unit.logger.log_manager.helpers import read_records


def test_info_record_is_structured_json(log_manager: LogManager, sink: BytesIO) -> None:
    """An INFO ``LogRecord`` becomes JSON with uvicorn's sentence as ``msg``."""
    handler = UvicornLogHandler(log_manager.get_child_logger("uvicorn"))
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Started server process [%d]",
        args=(1234,),
        exc_info=None,
    )

    handler.emit(record)

    (line,) = read_records(sink)
    assert line["context"] == "uvicorn"
    assert line["level"] == "info"
    assert line["msg"] == "Started server process [1234]"


def test_error_record_includes_exception(log_manager: LogManager, sink: BytesIO) -> None:
    """An ERROR record with ``exc_info`` carries the traceback in ``exception``."""
    handler = UvicornLogHandler(log_manager.get_child_logger("uvicorn"))
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.LogRecord(
            name="uvicorn.error",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="boom",
            args=(),
            exc_info=sys.exc_info(),
        )

    handler.emit(record)

    (line,) = read_records(sink)
    assert line["context"] == "uvicorn"
    assert line["level"] == "error"
    assert line["msg"] == "boom"
    assert "RuntimeError: boom" in line["exception"]
    assert "Traceback" in line["exception"]
