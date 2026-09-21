"""HTTP through the real application against throwaway Redis and PostgreSQL.

The next router adds ``tests/e2e/routes/<name>_router/`` and reuses ``client``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import AppConfig
from app.lifecycle import LifecycleManager
from app.state import get_app_state_from_app

if TYPE_CHECKING:
    from tests.throwaway_stores import ThrowawayStores

_E2E_ROOT: Final = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test under this directory as ``e2e``.

    Args:
        items: The collected session. Tests outside this tree are left unmarked.
    """
    e2e_marker = pytest.mark.e2e
    for item in items:
        try:
            item.path.relative_to(_E2E_ROOT)
        except ValueError:
            continue
        item.add_marker(e2e_marker)


def pytest_asyncio_loop_factories(
    config: pytest.Config,
    item: pytest.Item,
) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
    """Use a selector loop so psycopg async can connect on Windows.

    Linux and macOS already default to a selector loop. One factory keeps a
    single code path. Unit tests do not see this hook.

    Args:
        config: The pytest config. Required by the hook spec.
        item: The test item. Required by the hook spec.

    Returns:
        A single factory. pytest-asyncio hides the id when there is only one.
    """
    del config, item
    return {"selector": asyncio.SelectorEventLoop}


@pytest.fixture(scope="session")
def app(throwaway_stores: ThrowawayStores) -> FastAPI:
    """Build the real application pointed at the session containers.

    Args:
        throwaway_stores: Session Redis and PostgreSQL after Alembic has run.

    Returns:
        An application from ``LifecycleManager``. Lifespan has not run yet.
    """
    config = AppConfig(
        redis=throwaway_stores.redis,
        postgres=throwaway_stores.postgres,
    )
    return LifecycleManager(config).create_app()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Start the app lifespan once and yield an HTTP client.

    httpx 0.28's ``ASGITransport`` does not run lifespan, so this fixture
    enters ``lifespan_context`` itself.

    Args:
        app: Session application whose clients are started here.

    Yields:
        A client bound to the running application.
    """
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://e2e.test",
        ) as http,
    ):
        yield http


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _flush_redis(  # pyright: ignore[reportUnusedFunction]
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Empty Redis before every test so a later router does not inherit keys.

    Args:
        client: Session client. Requested so lifespan has already started Redis.
        app: Session application whose Redis pool is flushed.
    """
    del client
    await get_app_state_from_app(app).clients.redis.raw.flushdb()  # pyright: ignore[reportUnknownMemberType]
