"""HTTP surface for reading and writing tenant-scoped feature flags."""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.models.feature_flags import FeatureFlag, FeatureFlagSetRequest
from app.routes.get_user_details import UserDetailsDep
from app.routes.route_child_logger import RouteLogger
from app.services import FeatureFlagNotFoundError, FeatureFlagService
from app.state import get_feature_flag_service

feature_flag_router: Final = APIRouter(
    prefix="/api/v1/feature-flags",
    tags=["feature-flags"],
)

_FlagName = Annotated[
    str,
    Path(
        min_length=1,
        description="Identifier of the flag within the caller's tenant.",
        examples=["dark_mode"],
    ),
]

_GET_DESCRIPTION: Final = (
    "Return the current value of a named flag for the tenant in the X-Tenant-ID header, "
    "including when it last changed and which user last wrote it."
)
_PUT_DESCRIPTION: Final = (
    "Create or update a named flag for the tenant in the X-Tenant-ID header. "
    "The writing user is taken from X-User-ID and stored as the last editor. "
    "The name is taken from the path so the body cannot rename the resource."
)


@feature_flag_router.get(
    "/{name}",
    name="feature-flag-router.get",
    operation_id="getFeatureFlag",
    summary="Get a feature flag",
    description=_GET_DESCRIPTION,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No flag with that name for this tenant."},
    },
)
async def get_feature_flag(
    name: _FlagName,
    user_details: UserDetailsDep,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    logger: RouteLogger,
) -> FeatureFlag:
    """Return the current value of a named flag for the caller's tenant.

    Args:
        name: Identifier of the flag within the caller's tenant.
        user_details: Tenant and user from the inbound headers.
        service: Injected by FastAPI from application state.
        logger: Route-named child logger. The only logger a handler may use.

    Returns:
        The flag, including when it last changed and who last wrote it.

    Raises:
        HTTPException: 404 if the service has no row for this tenant and ``name``.
    """
    logger.info("feature_flag.get", name=name)
    try:
        return await service.get_flag(name, user_details)
    except FeatureFlagNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@feature_flag_router.put(
    "/{name}",
    name="feature-flag-router.set",
    operation_id="setFeatureFlag",
    summary="Set a feature flag",
    description=_PUT_DESCRIPTION,
    status_code=status.HTTP_200_OK,
)
async def set_feature_flag(
    name: _FlagName,
    body: FeatureFlagSetRequest,
    user_details: UserDetailsDep,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    logger: RouteLogger,
) -> FeatureFlag:
    """Create or update a named flag for the caller's tenant.

    Args:
        name: Identifier of the flag. Taken from the path so the body
            cannot rename the resource.
        body: The value to persist.
        user_details: Tenant and user from the inbound headers. The user id
            is stored as the last editor.
        service: Injected by FastAPI from application state.
        logger: Route-named child logger. The only logger a handler may use.

    Returns:
        The flag as stored, including the new ``updated_at`` and
        ``updated_by_user_id``.
    """
    logger.info("feature_flag.set", name=name, enabled=body.enabled)
    return await service.set_flag(name, body.enabled, user_details)
