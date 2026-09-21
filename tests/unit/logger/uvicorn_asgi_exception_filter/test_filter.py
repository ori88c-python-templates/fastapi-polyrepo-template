"""Drop uvicorn's ASGI traceback; keep unrelated uvicorn.error records."""

import logging

from app.logger import UvicornAsgiExceptionFilter


def test_asgi_exception_record_is_dropped() -> None:
    """The prefix uvicorn uses for a re-raised HTTP 500 must not be indexed twice."""
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Exception in ASGI application\n",
        args=(),
        exc_info=None,
    )
    assert UvicornAsgiExceptionFilter().filter(record) is False


def test_startup_record_is_kept() -> None:
    """Ordinary uvicorn lifecycle lines still reach the log."""
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Started server process",
        args=(),
        exc_info=None,
    )
    assert UvicornAsgiExceptionFilter().filter(record) is True
