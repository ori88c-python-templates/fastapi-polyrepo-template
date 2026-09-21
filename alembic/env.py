"""Alembic environment: a migration-owned engine plus the app's metadata and DSN.

This process is not the HTTP application. It builds its own SQLAlchemy engine from
the same ``POSTGRES__*`` settings and ``PostgresBase.metadata`` the app uses, and
never constructs ``PostgresClient``, a session factory, or ``LifecycleManager``.

The engine is synchronous on purpose. Alembic's operations are sync DDL; wrapping
them in ``create_async_engine`` only to call ``run_sync`` would couple migrations
to the application's event loop (and to psycopg's Windows Proactor restriction)
without changing what SQL runs.
"""

from logging.config import fileConfig
from typing import Final

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from app.clients.postgres.feature_flag_table import FeatureFlagRow
from app.clients.postgres.postgres_base import PostgresBase
from app.config import AppConfig, PostgresConfig

# Importing the row class registers it on PostgresBase.metadata for autogenerate.
_ORM_TABLES: Final = (FeatureFlagRow,)
_ = _ORM_TABLES

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = PostgresBase.metadata


def _postgres_settings() -> PostgresConfig:
    """Load ``POSTGRES__*`` from the same ``AppConfig`` the application uses.

    Redis settings must be present in the environment; this function does not open a
    Redis socket. The DSN is never logged.

    Returns:
        Validated PostgreSQL settings, including connect timeout.
    """
    # AppConfig reads redis and postgres from the environment; the type checker
    # cannot see that those fields are satisfied at runtime.
    app_config = AppConfig()  # pyright: ignore[reportCallIssue]
    return app_config.postgres


def run_migrations_offline() -> None:
    """Emit SQL to stdout without opening a database connection.

    Uses the DSN from the environment, not the placeholder in ``alembic.ini``.
    """
    context.configure(
        url=str(_postgres_settings().DSN),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure the Alembic context on a connection Alembic can drive.

    Args:
        connection: Sync connection from the migration-owned engine.
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database on a migration-owned sync engine.

    ``NullPool`` so the migration process does not hold a pool after it exits.
    ``connect_timeout`` comes from ``POSTGRES__CONNECT_TIMEOUT_SECONDS``. Statement
    timeout is omitted so slow DDL is not killed by the application's statement bound.
    """
    postgres = _postgres_settings()
    connectable = create_engine(
        str(postgres.DSN),
        poolclass=pool.NullPool,
        connect_args={
            "connect_timeout": postgres.CONNECT_TIMEOUT_SECONDS,
        },
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
