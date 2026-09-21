"""Run Alembic ``upgrade head`` against the session's throwaway PostgreSQL.

``alembic/env.py`` builds ``AppConfig()``, which reads ``.env`` then the process
environment. This module points env vars at the Testcontainers stores for the
upgrade so Compose on ``127.0.0.1:5432`` is never migrated, then restores env.
"""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from alembic import command
from alembic.config import Config

from tests.throwaway_stores import ThrowawayStores

_ALEMBIC_INI: Final = Path(__file__).resolve().parents[1] / "alembic.ini"
_ALEMBIC_ENV_KEYS: Final = (
    "POSTGRES__HOST",
    "POSTGRES__PORT",
    "POSTGRES__DATABASE",
    "POSTGRES__USER",
    "POSTGRES__PASSWORD",
    "POSTGRES__SSL_MODE",
    "REDIS__HOST",
    "REDIS__PORT",
    "REDIS__DB",
    "REDIS__USE_TLS",
    "REDIS__PASSWORD",
)


def upgrade_to_head(stores: ThrowawayStores) -> None:
    """Apply migrations and restore the process environment.

    Args:
        stores: Connection settings derived from the running containers.
    """
    previous = _snapshot_env(_ALEMBIC_ENV_KEYS)
    try:
        _apply_alembic_env(stores)
        command.upgrade(Config(str(_ALEMBIC_INI)), "head")
    finally:
        _restore_env(previous)


def _apply_alembic_env(stores: ThrowawayStores) -> None:
    """Point ``AppConfig`` at the throwaway containers for ``alembic upgrade``.

    Args:
        stores: Connection settings derived from the running containers.
    """
    os.environ.update(
        {
            "POSTGRES__HOST": stores.postgres.HOST,
            "POSTGRES__PORT": str(stores.postgres.PORT),
            "POSTGRES__DATABASE": stores.postgres.DATABASE,
            "POSTGRES__USER": stores.postgres.USER,
            "POSTGRES__PASSWORD": stores.postgres.PASSWORD.get_secret_value(),
            "POSTGRES__SSL_MODE": stores.postgres.SSL_MODE,
            "REDIS__HOST": stores.redis.HOST,
            "REDIS__PORT": str(stores.redis.PORT),
            "REDIS__DB": str(stores.redis.DB),
            "REDIS__USE_TLS": "true" if stores.redis.USE_TLS else "false",
        }
    )
    os.environ.pop("REDIS__PASSWORD", None)


def _snapshot_env(keys: tuple[str, ...]) -> dict[str, str | None]:
    """Capture the process environment for the keys Alembic might change.

    Args:
        keys: Names to restore after the upgrade.

    Returns:
        Current values, or ``None`` when a key is unset.
    """
    return {key: os.environ.get(key) for key in keys}


def _restore_env(previous: Mapping[str, str | None]) -> None:
    """Put ``os.environ`` back the way the caller found it.

    Args:
        previous: Snapshot from :func:`_snapshot_env`.
    """
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
