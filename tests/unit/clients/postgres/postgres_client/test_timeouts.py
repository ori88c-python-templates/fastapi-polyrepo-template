"""PostgresClient passes connect args and pool kwargs into the engine creator."""

from typing import cast
from unittest.mock import MagicMock

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from app.clients import PostgresClient
from app.config import PostgresConfig
from app.logger import LogManager


def test_create_async_engine_receives_timeouts_and_pool_kwargs(
    log_manager: LogManager,
) -> None:
    """Construction is lazy: the stand-in engine is never asked to connect."""
    config = PostgresConfig(
        HOST="127.0.0.1",
        DATABASE="app",
        USER="app",
        PASSWORD=SecretStr("secret"),
        CONNECT_TIMEOUT_SECONDS=3,
        STATEMENT_TIMEOUT_MS=7000,
        POOL_TIMEOUT_SECONDS=15,
    )
    engine = cast(AsyncEngine, MagicMock(spec=AsyncEngine))
    received: dict[str, object] = {}

    def capture(url: str, **kwargs: object) -> AsyncEngine:
        received["url"] = url
        received.update(kwargs)
        return engine

    client = PostgresClient(
        config,
        log_manager.get_child_logger("PostgresClient"),
        engine_creator=capture,
    )
    assert client.raw is engine
    assert received == {
        "url": str(config.DSN),
        "connect_args": {
            "connect_timeout": 3,
            "options": "-c statement_timeout=7000",
        },
        "pool_pre_ping": True,
        "pool_timeout": 15,
    }
