"""HTTP surface for reading and writing named feature flags."""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.models.feature_flags import FeatureFlag, FeatureFlagSetRequest
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
        description="Unique identifier of the flag.",
        examples=["dark_mode"],
    ),
]


@feature_flag_router.get(
    "/{name}",
    name="feature-flag-router.get",
    operation_id="getFeatureFlag",
    summary="Get a feature flag",
    description="Return the current value of a named flag, including when it last changed.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No flag with that name."},
    },
)
async def get_feature_flag(
    name: _FlagName,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    logger: RouteLogger,
) -> FeatureFlag:
    """Return the current value of a named flag.

    Args:
        name: Unique identifier of the flag.
        service: Injected by FastAPI from application state.
        logger: Route-named child logger. The only logger a handler may use.

    Returns:
        The flag, including when it last changed.

    Raises:
        HTTPException: 404 if the service has no row for ``name``.
    """
    logger.info("feature_flag.get", name=name)
    try:
        return await service.get_flag(name)
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
    description=(
        "Create or update a named flag. The name is taken from the path so the body "
        "cannot rename the resource."
    ),
    status_code=status.HTTP_200_OK,
)
async def set_feature_flag(
    name: _FlagName,
    body: FeatureFlagSetRequest,
    service: Annotated[FeatureFlagService, Depends(get_feature_flag_service)],
    logger: RouteLogger,
) -> FeatureFlag:
    """Create or update a named flag.

    Args:
        name: Unique identifier of the flag. Taken from the path so the body
            cannot rename the resource.
        body: The value to persist.
        service: Injected by FastAPI from application state.
        logger: Route-named child logger. The only logger a handler may use.

    Returns:
        The flag as stored, including the new ``updated_at``.
    """
    logger.info("feature_flag.set", name=name, enabled=body.enabled)
    return await service.set_flag(name, body.enabled)
