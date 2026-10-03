"""Caller headers are on the request's feature-flag logs and gone afterwards."""

from http import HTTPStatus
from io import BytesIO
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.state import get_app_state_from_app
from tests.e2e.routes.feature_flag_router.helpers import caller_headers
from tests.unit.logger.log_manager.helpers import read_records

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/api/v1/feature-flags/dark_mode"


def _records_after(stream: BytesIO, start: int) -> list[dict[str, Any]]:
    """Parse log lines written to ``stream`` after ``start``.

    Args:
        stream: Session buffer the application writes JSON lines to.
        start: Byte offset captured before the request.

    Returns:
        Records emitted after that offset, in order.
    """
    return read_records(BytesIO(stream.getvalue()[start:]))


async def test_request_logs_include_the_caller_then_drop_it(
    client: AsyncClient,
    app: FastAPI,
    e2e_log_stream: BytesIO,
) -> None:
    """Route and service lines carry both ids. A later line on the same manager does not."""
    start = len(e2e_log_stream.getvalue())
    response = await client.put(
        _PATH,
        json={"enabled": True},
        headers=caller_headers(),
    )

    assert response.status_code == HTTPStatus.OK
    records = _records_after(e2e_log_stream, start)
    feature_logs = [record for record in records if str(record["msg"]).startswith("feature_flag.")]
    assert any(record["msg"] == "feature_flag.set" for record in feature_logs)
    assert any(record["msg"] == "feature_flag.written" for record in feature_logs)
    for record in feature_logs:
        assert record["tenant_id"] == "tenant-a"
        assert record["user_id"] == "user-1"

    after_start = len(e2e_log_stream.getvalue())
    get_app_state_from_app(app).log_manager.get_child_logger("after-request").info(
        "feature_flag.after",
    )
    (after,) = _records_after(e2e_log_stream, after_start)
    assert after["msg"] == "feature_flag.after"
    assert "tenant_id" not in after
    assert "user_id" not in after
