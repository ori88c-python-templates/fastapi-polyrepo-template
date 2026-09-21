"""Typed container for everything the application builds once and keeps for its lifetime."""

from dataclasses import dataclass

from app.clients import PostgresClient, RedisClient
from app.logger import LogManager
from app.services import FeatureFlagService


@dataclass(frozen=True, slots=True)
class AppClients:
    """Clients for external resources such as Redis and PostgreSQL.

    Declare fields in topological order: a client must appear after everything
    it depends on, because that same order drives startup, and its reverse
    drives shutdown. Redis and PostgreSQL are independent of each other; Redis
    is first by convention.

    Attributes:
        redis: Process-wide Redis connection pool.
        postgres: Process-wide SQLAlchemy async engine.
    """

    redis: RedisClient
    postgres: PostgresClient


@dataclass(frozen=True, slots=True)
class AppServices:
    """Business services, each constructed with the clients and child logger it needs.

    A service never reaches for a client; the composition root hands it the ones
    it declared.

    Attributes:
        feature_flag: Reads and writes named flags through Redis and PostgreSQL.
    """

    feature_flag: FeatureFlagService


@dataclass(frozen=True, slots=True)
class AppState:
    """Everything created at startup and shared for the process lifetime.

    Frozen and slotted on purpose. FastAPI keeps application state in an untyped bag,
    so this is the only thing standing between the app and a stringly-typed dictionary:
    freezing stops a request handler from swapping a dependency mid-flight, and slots
    turn a typo'd attribute into an ``AttributeError`` at the assignment rather than a
    silently ignored write.

    This package sits below the HTTP layer so route handlers can depend on the
    accessors without importing the composition root, which would be an upward
    import and a cycle.

    Attributes:
        clients: Connections to external resources.
        services: Business logic, built on top of ``clients``.
        log_manager: Source of every child logger. A direct field rather than a client,
            because it owns no connection and is needed before any client is built.
    """

    clients: AppClients
    services: AppServices
    log_manager: LogManager
