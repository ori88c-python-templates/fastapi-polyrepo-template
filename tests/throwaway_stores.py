"""Throwaway Redis and PostgreSQL for integration and e2e sessions.

Not pytest fixtures: :func:`start_throwaway_stores` is a context manager
``tests/conftest.py`` turns into ``throwaway_stores``.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Final, NamedTuple

import docker  # type: ignore[import-untyped]
import pytest
from docker.errors import DockerException  # type: ignore[import-untyped]
from pydantic import SecretStr
from testcontainers.community.postgres import (  # type: ignore[import-untyped]
    PostgresContainer,
)
from testcontainers.community.redis import RedisContainer  # type: ignore[import-untyped]

from app.config import PostgresConfig, RedisConfig

_LOOPBACK_HOST: Final = "127.0.0.1"


class ThrowawayStores(NamedTuple):
    """Connection settings for the session's throwaway Redis and PostgreSQL."""

    postgres: PostgresConfig
    redis: RedisConfig


@contextmanager
def start_throwaway_stores() -> Generator[ThrowawayStores]:
    """Start Postgres 17 and Redis 7, then tear both down.

    Random host ports avoid Compose on ``127.0.0.1:5432`` / ``6379``. Host is
    always loopback IPv4 so Windows Docker Desktop does not stall on IPv6.

    Yields:
        Config objects pointed at the running containers, not Compose.
    """
    skip_without_docker()
    with (
        PostgresContainer("postgres:17-alpine") as postgres,
        RedisContainer("redis:7-alpine") as redis,
    ):
        yield ThrowawayStores(
            postgres=_postgres_config(postgres),
            redis=_redis_config(redis),
        )


def skip_without_docker() -> None:
    """Skip the calling test when the Docker daemon is not reachable."""
    try:
        client = docker.from_env()
        reachable = client.ping()  # pyright: ignore[reportUnknownMemberType]
    except DockerException as exc:
        pytest.skip(f"Docker is required for these tests ({exc}).")
    if reachable is not True:
        pytest.skip("Docker is required for these tests.")


def _postgres_config(postgres: PostgresContainer) -> PostgresConfig:
    """Map a running Postgres container onto ``PostgresConfig``.

    Args:
        postgres: Started Testcontainers Postgres.

    Returns:
        Settings using IPv4 loopback and ``sslmode=disable``.
    """
    return PostgresConfig(
        HOST=_LOOPBACK_HOST,
        PORT=int(postgres.get_exposed_port(postgres.port)),
        DATABASE=postgres.dbname,
        USER=postgres.username,
        PASSWORD=SecretStr(str(postgres.password)),
        SSL_MODE="disable",
    )


def _redis_config(redis: RedisContainer) -> RedisConfig:
    """Map a running Redis container onto ``RedisConfig``.

    Args:
        redis: Started Testcontainers Redis.

    Returns:
        Unauthenticated settings using IPv4 loopback.
    """
    return RedisConfig(
        HOST=_LOOPBACK_HOST,
        PORT=int(redis.get_exposed_port(redis.port)),
        DB=0,
        USE_TLS=False,
    )
