"""Unhandled errors become a generic 500 and a structured ``uvicorn`` log line."""

from http import HTTPStatus
from io import BytesIO
from uuid import UUID

from httpx import AsyncClient

from app.config import REQUEST_ID_HEADER
from tests.unit.logger.log_manager.helpers import read_records


async def test_unhandled_exception_returns_generic_500_and_logs_json(
    client: AsyncClient,
    sink: BytesIO,
) -> None:
    """The body is Starlette's generic 500; the traceback is only in the log."""
    response = await client.get("/boom")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.text == "Internal Server Error"
    assert "boom" not in response.text

    correlation_id = response.headers[REQUEST_ID_HEADER]
    UUID(correlation_id)

    (record,) = read_records(sink)
    assert record["context"] == "uvicorn"
    assert record["msg"] == "http.unhandled_exception"
    assert record["level"] == "error"
    assert record["correlation_id"] == correlation_id
    assert "RuntimeError: boom" in record["exception"]
    assert "Traceback" in record["exception"]
