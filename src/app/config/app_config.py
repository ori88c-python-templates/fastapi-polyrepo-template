"""The application's root configuration model."""

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.feature_flag_config import FeatureFlagConfig
from app.config.logger_config import LoggerConfig, LogLevel
from app.config.postgres_config import PostgresConfig
from app.config.prometheus_config import PrometheusConfig
from app.config.redis_config import RedisConfig
from app.config.server_config import ServerConfig


class Environment(StrEnum):
    """The deployment environment the process is running in.

    ``LOCAL`` is a developer machine, as distinct from ``DEV``, which is a shared
    deployed environment.
    """

    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

    def include_probes_in_schema(self) -> bool:
        """Whether Kubernetes probes appear in the generated OpenAPI schema.

        Local and shared-dev include them so Swagger on a developer machine is
        complete. Staging and production omit them: kubelet is the only caller,
        and the paths are not product API.

        Returns:
            True when this environment is ``local`` or ``dev``.
        """
        return self in (Environment.LOCAL, Environment.DEV)


class AppConfig(BaseSettings):
    """Root configuration, composed of one model per resource.

    Values are read from the process environment and from ``.env``. Names follow the
    nested model path, joined by ``__``: ``AppConfig.postgres.HOST`` comes from
    ``POSTGRES__HOST``. Matching is case-insensitive, so environment variables are
    written in upper case by convention.

    ``redis`` and ``postgres`` have no defaults: a deployment that fails to supply them
    fails at startup rather than at first use.

    Attributes:
        ENV: The deployment environment.
        server: HTTP server bind settings.
        logger: Structured logging settings.
        redis: Redis connection settings.
        postgres: PostgreSQL connection settings.
        feature_flag: Feature-flag cache settings. Optional in the environment;
            the default TTL is five minutes.
        prometheus: Scrape-endpoint settings. Optional in the environment;
            gzip defaults to off.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    ENV: Environment = Environment.DEV
    server: ServerConfig = Field(default_factory=ServerConfig)
    logger: LoggerConfig = Field(default_factory=LoggerConfig)
    redis: RedisConfig
    postgres: PostgresConfig
    feature_flag: FeatureFlagConfig = Field(default_factory=FeatureFlagConfig)
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)

    @model_validator(mode="after")
    def _enforce_production_invariants(self) -> Self:
        """Reject configurations that are individually valid but wrong for production.

        Each resource model can only validate itself. Rules that span models, such as
        "debug logging is never acceptable in production", have to live here.

        Returns:
            The validated model.

        Raises:
            ValueError: If ``ENV`` is ``prod`` and a setting is unsafe for production.
        """
        if self.ENV is not Environment.PROD:
            return self

        if self.logger.MIN_LOG_LEVEL is LogLevel.DEBUG:
            raise ValueError(
                "LOGGER__MIN_LOG_LEVEL=debug is not allowed when ENV=prod: "
                "debug logging risks writing sensitive payloads to the log stream."
            )

        if self.postgres.SSL_MODE == "disable":
            raise ValueError(
                "POSTGRES__SSL_MODE=disable is not allowed when ENV=prod: "
                "database traffic must be encrypted in production."
            )

        return self
