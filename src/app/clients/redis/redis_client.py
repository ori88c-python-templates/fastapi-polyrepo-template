"""Wrapper around a redis-py async client with explicit lifecycle hooks."""

from typing import Final

from redis.asyncio import Redis
from structlog.typing import FilteringBoundLogger

from app.config import RedisConfig


class RedisClient:
    """Owns one Redis connection pool for the process lifetime.

    Construction does not talk to the network: ``Redis.from_url`` is lazy. ``start``
    (and ``ping``) are what actually open a connection, which is why they run in the
    composition root's topological init rather than in ``__init__``.

    Attributes:
        raw: The wrapped redis-py client, for services that need to run commands.
    """

    def __init__(
        self,
        config: RedisConfig,
        logger: FilteringBoundLogger,
        *,
        client: Redis | None = None,
    ) -> None:
        """Build the wrapper. Does not connect.

        Args:
            config: Already-validated connection settings. The DSN is consumed here
                and never logged.
            logger: Child logger named after this class, injected by the composition
                root so this client does not build its own.
            client: Optional pre-built redis-py client. Production leaves this unset;
                tests pass a stand-in so nothing binds a real socket.
        """
        self._logger: Final = logger
        # redis-py types ``from_url`` with ``**kwargs: Unknown``, which leaks through
        # strict mode. The return is a ``Redis``; decode_responses makes values ``str``.
        self._client: Final[Redis] = (
            client
            if client is not None
            else Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
                str(config.DSN),
                decode_responses=True,
                socket_connect_timeout=config.CONNECT_TIMEOUT_SECONDS,
                socket_timeout=config.COMMAND_TIMEOUT_SECONDS,
                retry_on_timeout=False,
            )
        )

    @property
    def raw(self) -> Redis:
        """The wrapped redis-py client.

        Services issue commands through this rather than through one-off helpers on
        the wrapper, so the wrapper stays a lifecycle and health object.

        Returns:
            The client constructed in ``__init__``. Responses are decoded to ``str``.
        """
        return self._client

    async def start(self) -> None:
        """Open a connection by pinging the server.

        Raises:
            redis.exceptions.RedisError: If the server cannot be reached or PING
                fails. The composition root treats this as a failed startup.
        """
        self._logger.info("redis.starting")
        await self.ping()
        self._logger.info("redis.started")

    async def stop(self) -> None:
        """Close the connection pool.

        Safe to call if ``start`` never succeeded: redis-py closes an unused pool
        without requiring a prior connection.
        """
        self._logger.info("redis.stopping")
        await self._client.aclose()
        self._logger.info("redis.stopped")

    async def ping(self) -> None:
        """Confirm the existing pool can talk to Redis.

        Used by ``start`` and by the readiness probe. A failed ping raises; it does
        not return ``False``, so callers cannot ignore an unhealthy dependency.

        Raises:
            redis.exceptions.RedisError: If the command fails or the connection
                cannot be established.
            ConnectionError: If PING returns a value other than ``True``.
        """
        try:
            # redis-py types ``ping`` with ``**kwargs: Unknown``.
            pong = await self._client.ping()  # pyright: ignore[reportUnknownMemberType]
        except Exception:
            self._logger.exception("redis.ping.failed")
            raise
        if pong is not True:
            self._logger.error("redis.ping.unexpected_result", result=pong)
            raise ConnectionError("Redis PING did not return True.")
