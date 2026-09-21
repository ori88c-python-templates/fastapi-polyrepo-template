"""Wrapper around a SQLAlchemy async engine with explicit lifecycle hooks."""

from typing import Final

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from structlog.typing import FilteringBoundLogger

from app.config import PostgresConfig


class PostgresClient:
    """Owns one SQLAlchemy async engine for the process lifetime.

    Construction does not talk to the network: ``create_async_engine`` is lazy.
    ``start`` (and ``ping``) are what actually check out a connection, which is
    why they run in the composition root's topological init rather than in
    ``__init__``.

    Attributes:
        raw: The wrapped engine, for anything that cannot go through a session.
    """

    def __init__(
        self,
        config: PostgresConfig,
        logger: FilteringBoundLogger,
        *,
        engine: AsyncEngine | None = None,
    ) -> None:
        """Build the wrapper. Does not connect.

        Args:
            config: Already-validated connection settings. The DSN is consumed here
                and never logged.
            logger: Child logger named after this class, injected by the composition
                root so this client does not build its own.
            engine: Optional pre-built engine. Production leaves this unset; tests
                pass a stand-in so nothing binds a real socket.
        """
        self._logger: Final = logger
        # Pool size and overflow stay at SQLAlchemy's defaults (5 / 10); clones
        # should size them for the node's cores. ``pool_pre_ping`` detects a
        # dropped connection after a network hiccup. Alembic uses ``NullPool``
        # and must not copy these kwargs.
        self._engine: Final = (
            engine
            if engine is not None
            else create_async_engine(
                str(config.DSN),
                connect_args=config.connect_args,
                pool_pre_ping=True,
                pool_timeout=config.POOL_TIMEOUT_SECONDS,
            )
        )
        self._session_factory: Final = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

    @property
    def raw(self) -> AsyncEngine:
        """The wrapped SQLAlchemy engine.

        Prefer ``create_session`` for ordinary work. The engine is exposed for
        the rare case a caller needs something the session factory does not
        provide.

        Returns:
            The engine constructed in ``__init__``.
        """
        return self._engine

    def create_session(self) -> AsyncSession:
        """Open a new async session bound to this client's engine.

        Callers must use it as an async context manager and commit explicitly
        when they write. Closing without a commit rolls the transaction back.

        Returns:
            A session whose ``expire_on_commit`` is off, so loaded attributes
            remain usable after ``commit``.
        """
        return self._session_factory()

    async def start(self) -> None:
        """Open a connection by running a cheap ``SELECT 1``.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If the server cannot be reached. The
                composition root treats this as a failed startup.
        """
        self._logger.info("postgres.starting")
        await self.ping()
        self._logger.info("postgres.started")

    async def stop(self) -> None:
        """Dispose of the connection pool.

        Safe to call if ``start`` never succeeded: disposing an unused engine
        does not require a prior connection.
        """
        self._logger.info("postgres.stopping")
        await self._engine.dispose()
        self._logger.info("postgres.stopped")

    async def ping(self) -> None:
        """Confirm the existing pool can talk to PostgreSQL.

        Used by ``start`` and by the readiness probe. A failed ping raises; it
        does not return ``False``, so callers cannot ignore an unhealthy
        dependency. ``SELECT 1`` is the stand-in for a protocol-level PING,
        which the driver does not expose.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If the statement fails or the
                connection cannot be established.
        """
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            self._logger.exception("postgres.ping.failed")
            raise
