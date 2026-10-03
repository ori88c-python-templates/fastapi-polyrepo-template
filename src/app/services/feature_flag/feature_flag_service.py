"""Feature-flag reads and writes, cached in Redis and stored in PostgreSQL."""

from datetime import UTC, datetime
from typing import Final

from structlog.typing import FilteringBoundLogger

from app.clients import PostgresClient, RedisClient, create_redis_key
from app.clients.postgres import FeatureFlagRow
from app.config import FeatureFlagConfig
from app.metrics import FeatureFlagMetrics
from app.models.feature_flags import FeatureFlag
from app.models.user_details import UserDetails
from app.services.feature_flag.feature_flag_errors import FeatureFlagNotFoundError

_CACHE_KEY_PREFIX: Final = "feature_flag"


class FeatureFlagService:
    """Read and write tenant-scoped flags, with Redis as a TTL cache in front of PostgreSQL.

    No start or stop: the clients it uses already own those hooks. Constructed
    once by the composition root and stored on ``AppServices``. Caller identity
    is a method argument, not a constructor dependency: one instance serves
    every tenant.
    """

    def __init__(
        self,
        postgres: PostgresClient,
        redis: RedisClient,
        config: FeatureFlagConfig,
        logger: FilteringBoundLogger,
        metrics: FeatureFlagMetrics,
    ) -> None:
        """Store dependencies. Does not talk to Redis or PostgreSQL.

        Args:
            postgres: Session factory for the ``feature_flags`` table.
            redis: Cache. Keys are written and read through ``raw``.
            config: Supplies the cache TTL.
            logger: Child logger named after this class.
            metrics: Read and write counters, injected so this service does not
                own a process-wide Prometheus registry.
        """
        self._postgres: Final = postgres
        self._redis: Final = redis
        self._config: Final = config
        self._logger: Final = logger
        self._metrics: Final = metrics
        self._cache_ttl_seconds: Final = config.CACHE_TTL_SECONDS

    async def get_flag(self, name: str, user_details: UserDetails) -> FeatureFlag:
        """Return a flag for the caller's tenant, preferring Redis.

        A cache hit never touches the database. A miss loads the row, stores the
        full JSON (so ``updated_at`` and ``updated_by_user_id`` survive a hit),
        and returns it. A missing row is an error, not ``enabled=False``: an
        unknown flag is not the same as a disabled one. A row stored for another
        tenant is missing for this caller.

        Args:
            name: Identifier of the flag within the caller's tenant.
            user_details: Caller. ``tenant_id`` selects the row. ``user_id`` is
                not part of the lookup.

        Returns:
            The flag as the API speaks it.

        Raises:
            FeatureFlagNotFoundError: If this tenant has no row for ``name`` in
                Redis or PostgreSQL.
        """
        cache_key = self._cache_key(user_details.tenant_id, name)
        self._metrics.reads_total.inc()
        cached = await self._redis.raw.get(cache_key)
        if cached is not None:
            self._logger.info("feature_flag.cache.hit", name=name)
            return FeatureFlag.model_validate_json(cached)

        self._logger.info("feature_flag.cache.miss", name=name)
        async with self._postgres.create_session() as session:
            row = await session.get(FeatureFlagRow, (user_details.tenant_id, name))
            if row is None:
                self._logger.info("feature_flag.missing", name=name)
                raise FeatureFlagNotFoundError(name)
            flag = _row_to_flag(row)

        await self._write_cache(cache_key, flag)
        return flag

    async def set_flag(self, name: str, enabled: bool, user_details: UserDetails) -> FeatureFlag:
        """Insert or update a flag for the caller's tenant, then refresh Redis.

        The ORM path is ``session.get`` plus ``add`` or in-place mutation, not a
        dialect-specific upsert, so the write stays in mapped-class terms.
        Redis is updated (not only deleted) after commit so the next read does
        not stampede the database. ``updated_by_user_id`` is the caller's user
        id on both insert and update.

        Args:
            name: Identifier of the flag within the caller's tenant.
            enabled: The value to persist.
            user_details: Caller. ``tenant_id`` selects the row.
                ``user_id`` is stored as the last editor.

        Returns:
            The flag as stored, including the new ``updated_at``.
        """
        now = datetime.now(UTC)
        async with self._postgres.create_session() as session:
            row = await session.get(FeatureFlagRow, (user_details.tenant_id, name))
            if row is None:
                session.add(
                    FeatureFlagRow(
                        tenant_id=user_details.tenant_id,
                        name=name,
                        value=enabled,
                        updated_at=now,
                        updated_by_user_id=user_details.user_id,
                    ),
                )
            else:
                row.value = enabled
                row.updated_at = now
                row.updated_by_user_id = user_details.user_id
            await session.commit()

        flag = FeatureFlag(
            name=name,
            enabled=enabled,
            updated_at=now,
            updated_by_user_id=user_details.user_id,
        )
        await self._write_cache(self._cache_key(user_details.tenant_id, name), flag)
        self._metrics.writes_total.inc()
        self._logger.info("feature_flag.written", name=name, enabled=enabled)
        return flag

    async def _write_cache(self, cache_key: str, flag: FeatureFlag) -> None:
        """Store ``flag`` in Redis under ``cache_key`` with the configured TTL.

        Args:
            cache_key: Already-prefixed Redis key.
            flag: The domain model to serialise. JSON rather than a lone boolean
                so a cache hit can still return ``updated_at`` and
                ``updated_by_user_id``.
        """
        await self._redis.raw.set(
            cache_key,
            flag.model_dump_json(),
            ex=self._cache_ttl_seconds,
        )

    @staticmethod
    def _cache_key(tenant_id: str, name: str) -> str:
        """Build the Redis key for one tenant's flag.

        Args:
            tenant_id: Tenant the flag belongs to.
            name: Identifier of the flag within that tenant.

        Returns:
            A length-prefixed key so a colon inside either part cannot merge
            this flag with another tenant's row.
        """
        return create_redis_key(_CACHE_KEY_PREFIX, tenant_id, name)


def _row_to_flag(row: FeatureFlagRow) -> FeatureFlag:
    """Map a persistence row onto the API model.

    Args:
        row: Loaded ORM instance. ``value`` becomes ``enabled``.

    Returns:
        The equivalent domain object. The tenant stays off the API model.
    """
    return FeatureFlag(
        name=row.name,
        enabled=row.value,
        updated_at=row.updated_at,
        updated_by_user_id=row.updated_by_user_id,
    )
