"""Default security-header middleware from the ``secure`` package."""

from typing import Final

from secure import Secure  # type: ignore[import-untyped]
from secure.middleware import (  # type: ignore[import-untyped]
    SecureASGIMiddleware as _LibrarySecureASGIMiddleware,
)
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import REDOC_ENDPOINT, SWAGGER_DOCS_ENDPOINT

_DOCS_PATH_PREFIXES: Final = (SWAGGER_DOCS_ENDPOINT, REDOC_ENDPOINT)
_CSP_HEADER: Final = b"content-security-policy"


def default_secure_headers() -> Secure:
    """Return ``Preset.BALANCED`` headers, the package's recommended default.

    Returns:
        A ``Secure`` instance for ``SecureASGIMiddleware``.
    """
    return Secure.with_default_headers()


def _is_docs_path(path: str) -> bool:
    """Return whether ``path`` is Swagger UI or ReDoc, including nested routes.

    Args:
        path: ASGI HTTP path.

    Returns:
        True when BALANCED CSP would block the page's CDN scripts and inline
        bootstrap, so this adapter omits only ``Content-Security-Policy``.
    """
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in _DOCS_PATH_PREFIXES)


class SecureASGIMiddleware:
    """Adapter around the ``secure`` library that omits CSP on documentation pages.

    FastAPI cannot attach ASGI middleware to selected routes, and
    ``secure.SecureASGIMiddleware`` has no exclude list. This class always runs
    the library so BALANCED headers (HSTS, ``X-Content-Type-Options``,
    ``X-Frame-Options``, …) land on every HTTP response. On ``/docs`` and
    ``/redoc`` it then drops ``Content-Security-Policy``: FastAPI's default
    Swagger UI and ReDoc HTML load jsDelivr plus an inline bootstrap that
    ``script-src 'self'`` would block.
    """

    def __init__(self, app: ASGIApp, *, secure: Secure | None = None) -> None:
        """Wrap ``app`` with the library middleware.

        Args:
            app: The next ASGI application in the stack. The composition root
                passes this in via ``add_middleware``; this class never installs
                itself.
            secure: Header set the library applies. ``None`` uses the library
                default, matching ``default_secure_headers``.
        """
        self._inner: Final = _LibrarySecureASGIMiddleware(app, secure=secure)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Apply BALANCED headers; omit CSP on documentation pages.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable. Documentation responses are wrapped so
                ``Content-Security-Policy`` is removed after the library injects
                it.
        """
        if scope["type"] == "http" and _is_docs_path(str(scope.get("path", ""))):
            await self._inner(scope, receive, _omit_csp(send))  # pyright: ignore[reportArgumentType]
            return
        await self._inner(scope, receive, send)  # pyright: ignore[reportArgumentType]


def _omit_csp(send: Send) -> Send:
    """Return a send callable that strips ``Content-Security-Policy``.

    Args:
        send: Downstream ASGI send.

    Returns:
        A send wrapper that leaves every other header the library set intact.
    """

    async def send_without_csp(message: Message) -> None:
        """Drop CSP on the response start; forward every other event unchanged.

        Args:
            message: An ASGI event. Only ``http.response.start`` is altered.
        """
        if message["type"] == "http.response.start":
            # The library stores mixed-case names; compare in lowercase.
            message["headers"] = [
                (name, value) for name, value in message["headers"] if name.lower() != _CSP_HEADER
            ]
        await send(message)

    return send_without_csp


__all__ = ["SecureASGIMiddleware", "default_secure_headers"]
