"""The correlation id must not leak onto the next task on the event loop."""

from io import BytesIO

from httpx import AsyncClient

from app.config import Environment, LoggerConfig
from app.logger import LogManager
from tests.unit.logger.log_manager.helpers import read_records


async def test_correlation_id_is_unbound_after_the_request(
    client: AsyncClient,
    sink: BytesIO,
) -> None:
    """A child logger created after the request must not inherit ``correlation_id``."""
    await client.get("/ping")
    (during,) = read_records(sink)
    assert "correlation_id" in during

    after_sink = BytesIO()
    LogManager(
        LoggerConfig(), env=Environment.DEV, app_version="0.1.0", stream=after_sink
    ).get_child_logger("after").info(
        "after.request",
    )

    (after,) = read_records(after_sink)
    assert "correlation_id" not in after
    assert set(after) == {
        "ts",
        "msg",
        "level",
        "context",
        "env",
        "app",
        "instance",
        "app.version",
    }
