"""Caller identity shared by routes and services."""

from pydantic import BaseModel, ConfigDict, Field


class UserDetails(BaseModel):
    """Tenant and user taken from the inbound HTTP headers.

    This is not an authentication credential. A missing or blank header fails
    validation before the route handler runs. Routes receive this object from
    ``Depends(get_user_details)`` and pass the same object into the service.

    Attributes:
        tenant_id: Non-empty tenant the caller belongs to.
        user_id: Non-empty user the caller is acting as.
    """

    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(min_length=1, description="Non-empty tenant id.")
    user_id: str = Field(min_length=1, description="Non-empty user id.")
