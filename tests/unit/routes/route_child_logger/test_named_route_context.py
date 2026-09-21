"""The injected route logger binds ``context`` to the explicit route name."""

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock

from httpx import AsyncClient

from app.models.feature_flags import FeatureFlag
from tests.unit.logger.log_manager.helpers import read_records

_FLAG = FeatureFlag(
    name="dark_mode",
    enabled=True,
    updated_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
)


async def test_get_emits_the_explicit_route_name_as_context(
    client: AsyncClient,
    feature_flag_service: AsyncMock,
    sink: BytesIO,
) -> None:
    """GET logs with ``context`` equal to the decorator's ``name=``, not the function name."""
    feature_flag_service.get_flag.return_value = _FLAG

    await client.get("/api/v1/feature-flags/dark_mode")

    (record,) = read_records(sink)
    assert record["context"] == "feature-flag-router.get"
    assert record["msg"] == "feature_flag.get"
    assert record["name"] == "dark_mode"


async def test_set_emits_the_explicit_route_name_as_context(
    client: AsyncClient,
    feature_flag_service: AsyncMock,
    sink: BytesIO,
) -> None:
    """PUT uses a distinct route name so get and set stay distinguishable in logs."""
    feature_flag_service.set_flag.return_value = _FLAG

    await client.put("/api/v1/feature-flags/dark_mode", json={"enabled": True})

    (record,) = read_records(sink)
    assert record["context"] == "feature-flag-router.set"
    assert record["msg"] == "feature_flag.set"
    assert record["name"] == "dark_mode"
    assert record["enabled"] is True
