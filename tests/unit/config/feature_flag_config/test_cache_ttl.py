"""Cache TTL default, rejection of zero, and constructed values."""

import pytest
from pydantic import ValidationError

from app.config import FeatureFlagConfig


def test_cache_ttl_defaults_to_five_minutes() -> None:
    """Omitted TTL still expires the Redis key instead of storing it forever."""
    assert FeatureFlagConfig().CACHE_TTL_SECONDS == 300


def test_cache_ttl_below_one_second_is_rejected() -> None:
    """Zero would mean no expiry on Redis ``SET EX``."""
    with pytest.raises(ValidationError):
        FeatureFlagConfig(CACHE_TTL_SECONDS=0)


def test_constructed_cache_ttl_round_trips() -> None:
    """An explicit TTL is stored as given so the service can pass it to Redis."""
    assert FeatureFlagConfig(CACHE_TTL_SECONDS=60).CACHE_TTL_SECONDS == 60
