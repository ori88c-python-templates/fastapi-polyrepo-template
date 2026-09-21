"""Assemble a real FeatureFlagService from the shared client doubles."""

from typing import cast
from unittest.mock import MagicMock

import pytest
from prometheus_client import CollectorRegistry

from app.clients import PostgresClient, RedisClient
from app.config import FeatureFlagConfig
from app.logger import LogManager
from app.metrics import FeatureFlagMetrics
from app.services import FeatureFlagService


@pytest.fixture
def collector_registry() -> CollectorRegistry:
    """Provide a private collector so metric tests cannot collide.

    Returns:
        An empty registry bound to this test's ``FeatureFlagMetrics``.
    """
    return CollectorRegistry()


@pytest.fixture
def feature_flag_metrics(collector_registry: CollectorRegistry) -> FeatureFlagMetrics:
    """Provide collectors registered on the test's private registry.

    Args:
        collector_registry: Empty registry for this test.

    Returns:
        Metrics the service under test will increment.
    """
    return FeatureFlagMetrics(registry=collector_registry)


@pytest.fixture
def feature_flag_service(
    postgres_client: MagicMock,
    redis_client: MagicMock,
    log_manager: LogManager,
    feature_flag_metrics: FeatureFlagMetrics,
) -> FeatureFlagService:
    """Provide the real service wired to mocked Redis and PostgreSQL.

    Args:
        postgres_client: Sync ``create_session`` returning the shared session mock.
        redis_client: Wrapper whose ``raw`` get/set are awaitable mocks.
        log_manager: Buffer-backed manager from the unit-test root.
        feature_flag_metrics: Collectors on this test's private registry.

    Returns:
        A ``FeatureFlagService`` that never opens a socket.
    """
    return FeatureFlagService(
        cast(PostgresClient, postgres_client),
        cast(RedisClient, redis_client),
        FeatureFlagConfig(),
        log_manager.get_child_logger("FeatureFlagService"),
        feature_flag_metrics,
    )
