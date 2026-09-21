"""HTTPException and 404 must not go through the unhandled ``uvicorn`` handler."""

from http import HTTPStatus
from io import BytesIO

from httpx import AsyncClient

from tests.unit.logger.log_manager.helpers import read_records


async def test_http_exception_is_not_logged_as_unhandled(
    client: AsyncClient,
    sink: BytesIO,
) -> None:
    """A 404 is a handled HTTP error, not an uncaught exception."""
    response = await client.get("/missing")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert read_records(sink) == []
