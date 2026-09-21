"""Empty this router's table before every test. Leaves ``alembic_version``."""

import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text

from app.state import get_app_state_from_app


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _truncate_feature_flags(  # pyright: ignore[reportUnusedFunction]
    client: AsyncClient,
    app: FastAPI,
) -> None:
    """Wipe ``feature_flags`` so a later test does not inherit rows.

    Args:
        client: Session client. Requested so lifespan has already started Postgres.
        app: Session application whose engine runs ``TRUNCATE``.
    """
    del client
    postgres = get_app_state_from_app(app).clients.postgres
    async with postgres.create_session() as session:
        await session.execute(text("TRUNCATE feature_flags"))
        await session.commit()
