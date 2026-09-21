"""OpenAPI documentation pages omit BALANCED CSP only."""

from http import HTTPStatus

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import REDOC_ENDPOINT, SWAGGER_DOCS_ENDPOINT
from app.middlewares import SecureASGIMiddleware, default_secure_headers


def _docs_app() -> FastAPI:
    """Application with FastAPI's default docs behind the secure adapter.

    Returns:
        An app whose ``/docs`` HTML would be blank if CSP were applied.
    """
    app = FastAPI()
    app.add_middleware(SecureASGIMiddleware, secure=default_secure_headers())
    return app


async def test_docs_page_omits_csp_and_keeps_other_secure_headers() -> None:
    """Swagger UI must load CDN scripts; MIME-sniffing protection still applies."""
    async with AsyncClient(
        transport=ASGITransport(app=_docs_app()),
        base_url="http://secure.test",
    ) as client:
        response = await client.get(SWAGGER_DOCS_ENDPOINT)

    assert response.status_code == HTTPStatus.OK
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "swagger-ui" in response.text


async def test_redoc_page_omits_csp_and_keeps_other_secure_headers() -> None:
    """ReDoc is the same class of CDN page as Swagger UI."""
    async with AsyncClient(
        transport=ASGITransport(app=_docs_app()),
        base_url="http://secure.test",
    ) as client:
        response = await client.get(REDOC_ENDPOINT)

    assert response.status_code == HTTPStatus.OK
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
