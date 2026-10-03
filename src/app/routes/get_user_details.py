"""Build ``UserDetails`` from the inbound HTTP headers.

Shared by feature routes that need a caller. There is no ASGI middleware for
these headers: a route ``Depends`` on this factory. The factory is an async
generator so ``tenant_id`` and ``user_id`` stay on the structlog context for
the handler, then unbind.

FastAPI wraps that generator with ``asynccontextmanager`` itself. Decorating
this function again would make the dependency a context-manager factory, which
FastAPI would not enter.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import Depends, Header
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.config import TENANT_ID_HEADER, USER_ID_HEADER
from app.models.user_details import UserDetails

_TenantId = Annotated[
    str,
    Header(
        alias=TENANT_ID_HEADER,
        description="Tenant this flag belongs to.",
        examples=["tenant-a"],
    ),
]
_UserId = Annotated[
    str,
    Header(
        alias=USER_ID_HEADER,
        description="User performing this call. A write is recorded as the last editor.",
        examples=["user-1"],
    ),
]


async def get_user_details(
    tenant_id: _TenantId,
    user_id: _UserId,
) -> AsyncGenerator[UserDetails]:
    """Yield the caller, with tenant and user bound on the log context.

    FastAPI enters this generator before the handler and closes it after the
    response, so the route logger and the service logger both pick up the ids.
    The bind ends with the call. A missing header never reaches this function:
    FastAPI rejects it while binding the parameters. A blank value is rejected
    here, before anything is bound.

    Args:
        tenant_id: Raw ``X-Tenant-ID`` value. Stripped before validation.
        user_id: Raw ``X-User-ID`` value. Stripped before validation.

    Yields:
        The validated tenant and user.

    Raises:
        RequestValidationError: If either header is blank after stripping.
    """
    try:
        user_details = UserDetails(tenant_id=tenant_id.strip(), user_id=user_id.strip())
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    with structlog.contextvars.bound_contextvars(
        tenant_id=user_details.tenant_id,
        user_id=user_details.user_id,
    ):
        yield user_details


UserDetailsDep = Annotated[UserDetails, Depends(get_user_details)]
