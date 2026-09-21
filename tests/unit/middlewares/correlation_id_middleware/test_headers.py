"""Inbound header selection and the outbound ``X-Request-ID``."""

from http import HTTPStatus
from io import BytesIO
from uuid import UUID

from httpx import AsyncClient

from app.config import CORRELATION_ID_HEADER, REQUEST_ID_HEADER
from tests.unit.logger.log_manager.helpers import read_records


async def test_missing_inbound_header_generates_a_uuid_returned_and_logged(
    client: AsyncClient,
    sink: BytesIO,
) -> None:
    """No inbound id still produces ``X-Request-ID`` and the same value in the log."""
    response = await client.get("/ping")

    assert response.status_code == HTTPStatus.OK
    correlation_id = response.headers[REQUEST_ID_HEADER]
    UUID(correlation_id)
    assert CORRELATION_ID_HEADER not in response.headers

    (record,) = read_records(sink)
    assert record["correlation_id"] == correlation_id
    assert record["msg"] == "ping.ok"


async def test_inbound_x_request_id_is_echoed(
    client: AsyncClient,
    sink: BytesIO,
) -> None:
    """A caller-supplied ``X-Request-ID`` is the id used for the response and the log."""
    inbound = "req-from-client"

    response = await client.get("/ping", headers={REQUEST_ID_HEADER: inbound})

    assert response.headers[REQUEST_ID_HEADER] == inbound
    (record,) = read_records(sink)
    assert record["correlation_id"] == inbound


async def test_inbound_x_correlation_id_is_returned_as_x_request_id(
    client: AsyncClient,
    sink: BytesIO,
) -> None:
    """``X-Correlation-ID`` is accepted inbound; the response still uses ``X-Request-ID``."""
    inbound = "corr-from-client"

    response = await client.get("/ping", headers={CORRELATION_ID_HEADER: inbound})

    assert response.headers[REQUEST_ID_HEADER] == inbound
    assert CORRELATION_ID_HEADER not in response.headers
    (record,) = read_records(sink)
    assert record["correlation_id"] == inbound


async def test_x_request_id_wins_when_both_headers_are_present(
    client: AsyncClient,
    sink: BytesIO,
) -> None:
    """When both inbound headers are set, ``X-Request-ID`` is the one that counts."""
    response = await client.get(
        "/ping",
        headers={
            REQUEST_ID_HEADER: "from-request-id",
            CORRELATION_ID_HEADER: "from-correlation-id",
        },
    )

    assert response.headers[REQUEST_ID_HEADER] == "from-request-id"
    (record,) = read_records(sink)
    assert record["correlation_id"] == "from-request-id"


async def test_unmatched_path_still_returns_x_request_id(client: AsyncClient) -> None:
    """A 404 is still an HTTP request, so it still gets a correlation id."""
    response = await client.get("/no-such-route")

    assert response.status_code == HTTPStatus.NOT_FOUND
    UUID(response.headers[REQUEST_ID_HEADER])
