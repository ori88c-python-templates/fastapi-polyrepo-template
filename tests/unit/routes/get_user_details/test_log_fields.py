"""Tenant and user ids are on logs inside get_user_details and gone after it."""

from contextlib import asynccontextmanager
from io import BytesIO

import pytest
from fastapi.exceptions import RequestValidationError

from app.logger import LogManager
from app.routes.get_user_details import get_user_details
from tests.unit.logger.log_manager.helpers import read_records

_INSIDE = "user_details.inside"
_OUTSIDE = "user_details.outside"


async def test_user_ids_are_bound_only_inside_get_user_details(
    log_manager: LogManager,
    sink: BytesIO,
) -> None:
    """A log inside the call carries both ids. A log after exit does not."""
    logger = log_manager.get_child_logger("user-details")
    async with asynccontextmanager(get_user_details)(tenant_id="tenant-a", user_id="user-1"):
        logger.info(_INSIDE)
    logger.info(_OUTSIDE)

    inside, outside = read_records(sink)
    assert inside["msg"] == _INSIDE
    assert inside["tenant_id"] == "tenant-a"
    assert inside["user_id"] == "user-1"
    assert outside["msg"] == _OUTSIDE
    assert "tenant_id" not in outside
    assert "user_id" not in outside


async def test_a_blank_header_does_not_bind(
    log_manager: LogManager,
    sink: BytesIO,
) -> None:
    """A blank header fails validation before either id is bound."""
    logger = log_manager.get_child_logger("user-details")
    with pytest.raises(RequestValidationError):
        async with asynccontextmanager(get_user_details)(tenant_id="  ", user_id="user-1"):
            logger.info(_INSIDE)
    logger.info(_OUTSIDE)

    (outside,) = read_records(sink)
    assert outside["msg"] == _OUTSIDE
    assert "tenant_id" not in outside
    assert "user_id" not in outside
