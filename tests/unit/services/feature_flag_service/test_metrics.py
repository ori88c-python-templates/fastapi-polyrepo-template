"""Business counters increment when the matching use case runs."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from prometheus_client import CollectorRegistry, generate_latest

from app.models.feature_flags import FeatureFlag
from app.models.user_details import UserDetails
from app.services import FeatureFlagService

_NAME = "dark_mode"
_CALLER = UserDetails(tenant_id="tenant-a", user_id="user-1")
_FLAG = FeatureFlag(
    name=_NAME,
    enabled=True,
    updated_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    updated_by_user_id=_CALLER.user_id,
)


async def test_get_flag_increments_reads_total(
    feature_flag_service: FeatureFlagService,
    redis_client: AsyncMock,
    collector_registry: CollectorRegistry,
) -> None:
    """A read is observable as scrape text on the service's registry."""
    redis_client.get_string.return_value = _FLAG.model_dump_json()

    await feature_flag_service.get_flag(_NAME, _CALLER)

    body = generate_latest(collector_registry).decode()
    assert "feature_flag_reads_total 1.0" in body


async def test_set_flag_increments_writes_total(
    feature_flag_service: FeatureFlagService,
    postgres_session: AsyncMock,
    collector_registry: CollectorRegistry,
) -> None:
    """A persisted write is observable as scrape text on the service's registry."""
    postgres_session.get.return_value = None

    await feature_flag_service.set_flag(_NAME, enabled=True, user_details=_CALLER)

    body = generate_latest(collector_registry).decode()
    assert "feature_flag_writes_total 1.0" in body
