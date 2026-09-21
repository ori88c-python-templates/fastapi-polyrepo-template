"""Timeout defaults, rejection of zero, and engine connect_args."""

import pytest
from pydantic import SecretStr, ValidationError

from app.config import PostgresConfig

_HOST: str = "127.0.0.1"
_DATABASE: str = "app"
_USER: str = "app"
_PASSWORD: SecretStr = SecretStr("secret")


def _config(
    *,
    connect_timeout_seconds: int = 5,
    statement_timeout_ms: int = 5000,
    pool_timeout_seconds: int = 30,
) -> PostgresConfig:
    """Build settings with only the fields a timeout test cares about."""
    return PostgresConfig(
        HOST=_HOST,
        DATABASE=_DATABASE,
        USER=_USER,
        PASSWORD=_PASSWORD,
        CONNECT_TIMEOUT_SECONDS=connect_timeout_seconds,
        STATEMENT_TIMEOUT_MS=statement_timeout_ms,
        POOL_TIMEOUT_SECONDS=pool_timeout_seconds,
    )


def test_timeouts_use_documented_defaults() -> None:
    """Omitted timeouts still bound a hung server or pool wait."""
    config = PostgresConfig(
        HOST=_HOST,
        DATABASE=_DATABASE,
        USER=_USER,
        PASSWORD=_PASSWORD,
    )
    assert config.CONNECT_TIMEOUT_SECONDS == 5
    assert config.STATEMENT_TIMEOUT_MS == 5000
    assert config.POOL_TIMEOUT_SECONDS == 30


def test_timeouts_below_one_are_rejected() -> None:
    """Zero would disable the bound; sub-unit values are not useful here."""
    with pytest.raises(ValidationError):
        _config(connect_timeout_seconds=0)
    with pytest.raises(ValidationError):
        _config(statement_timeout_ms=0)
    with pytest.raises(ValidationError):
        _config(pool_timeout_seconds=0)


def test_constructed_timeouts_round_trip() -> None:
    """An explicit triple is stored as given so the engine can apply each knob."""
    config = _config(
        connect_timeout_seconds=3,
        statement_timeout_ms=7000,
        pool_timeout_seconds=15,
    )
    assert config.CONNECT_TIMEOUT_SECONDS == 3
    assert config.STATEMENT_TIMEOUT_MS == 7000
    assert config.POOL_TIMEOUT_SECONDS == 15


def test_connect_args_maps_timeouts_for_the_app_engine() -> None:
    """The application engine gets libpq options; Alembic must not reuse this dict."""
    config = _config(connect_timeout_seconds=3, statement_timeout_ms=7000)
    assert config.connect_args == {
        "connect_timeout": 3,
        "options": "-c statement_timeout=7000",
    }
