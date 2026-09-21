"""PostgresClient passes connect args and pool kwargs into create_async_engine."""

from unittest.mock import MagicMock, patch

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from app.clients import PostgresClient
from app.config import PostgresConfig
from app.logger import LogManager


def test_create_async_engine_receives_timeouts_and_pool_kwargs(
    log_manager: LogManager,
) -> None:
    """Construction is lazy: the mock engine is never asked to connect."""
    config = PostgresConfig(
        HOST="127.0.0.1",
        DATABASE="app",
        USER="app",
        PASSWORD=SecretStr("secret"),
        CONNECT_TIMEOUT_SECONDS=3,
        STATEMENT_TIMEOUT_MS=7000,
        POOL_TIMEOUT_SECONDS=15,
    )
    engine = MagicMock(spec=AsyncEngine)
    with patch(
        "app.clients.postgres.postgres_client.create_async_engine",
        return_value=engine,
    ) as create:
        PostgresClient(config, log_manager.get_child_logger("PostgresClient"))
    create.assert_called_once_with(
        str(config.DSN),
        connect_args={
            "connect_timeout": 3,
            "options": "-c statement_timeout=7000",
        },
        pool_pre_ping=True,
        pool_timeout=15,
    )
