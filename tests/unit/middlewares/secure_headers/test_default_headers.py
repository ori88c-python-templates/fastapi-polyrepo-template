"""Default security headers appear on HTTP responses."""

from http import HTTPStatus

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import REQUEST_ID_HEADER
from app.middlewares import (
    CorrelationIdMiddleware,
    SecureASGIMiddleware,
    default_secure_headers,
)


def _ping_app() -> FastAPI:
    """Tiny app wrapped like ``LifecycleManager._add_middlewares_in_order``.

    Returns:
        An application exposing ``GET /ping`` behind Secure, then correlation id.
    """
    app = FastAPI()

    async def ping() -> dict[str, bool]:
        """Return a body the tests ignore.

        Returns:
            A trivial JSON payload.
        """
        return {"ok": True}

    app.add_api_route("/ping", ping)
    app.add_middleware(SecureASGIMiddleware, secure=default_secure_headers())
    app.add_middleware(CorrelationIdMiddleware)
    return app


async def test_default_headers_include_x_content_type_options() -> None:
    """Wiring check: BALANCED defaults actually reach the response.

    This does not prove CSP in a browser. It proves we mounted
    ``SecureASGIMiddleware`` with ``with_default_headers``.
    """
    async with AsyncClient(
        transport=ASGITransport(app=_ping_app()),
        base_url="http://secure.test",
    ) as client:
        response = await client.get("/ping")

    assert response.status_code == HTTPStatus.OK
    assert response.headers["X-Content-Type-Options"] == "nosniff"


async def test_secure_headers_coexist_with_x_request_id() -> None:
    """Correlation id stays outermost; security headers still land on the response."""
    async with AsyncClient(
        transport=ASGITransport(app=_ping_app()),
        base_url="http://secure.test",
    ) as client:
        response = await client.get("/ping")

    assert response.headers[REQUEST_ID_HEADER]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
