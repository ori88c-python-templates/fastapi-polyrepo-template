"""Timeout defaults, rejection of zero, and constructed values."""

import pytest
from pydantic import ValidationError

from app.config import RedisConfig


def test_timeouts_default_to_five_seconds() -> None:
    """Omitted timeouts still bound a hung socket instead of blocking forever."""
    config = RedisConfig(HOST="127.0.0.1")
    assert config.CONNECT_TIMEOUT_SECONDS == 5
    assert config.COMMAND_TIMEOUT_SECONDS == 5


def test_timeouts_below_one_second_are_rejected() -> None:
    """Zero would mean no expiry-like wait; redis-py treats 0 as a bound of zero."""
    with pytest.raises(ValidationError):
        RedisConfig(HOST="127.0.0.1", CONNECT_TIMEOUT_SECONDS=0)
    with pytest.raises(ValidationError):
        RedisConfig(HOST="127.0.0.1", COMMAND_TIMEOUT_SECONDS=0)


def test_constructed_timeouts_round_trip() -> None:
    """An explicit pair is stored as given so the client can apply both knobs."""
    config = RedisConfig(
        HOST="127.0.0.1",
        CONNECT_TIMEOUT_SECONDS=3,
        COMMAND_TIMEOUT_SECONDS=7,
    )
    assert config.CONNECT_TIMEOUT_SECONDS == 3
    assert config.COMMAND_TIMEOUT_SECONDS == 7
