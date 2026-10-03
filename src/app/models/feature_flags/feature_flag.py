"""The feature flag as the API and service layer speak it."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlag(BaseModel):
    """A named boolean flag, when it last changed, and who last wrote it.

    Distinct from the ORM row: this model uses ``enabled`` where the table uses
    ``value``, so a column rename is not automatically a breaking API change.
    The tenant is not a field here. Callers send it on ``X-Tenant-ID``, and the
    stored row is keyed by that tenant plus ``name``.

    Attributes:
        name: Identifier of the flag within the caller's tenant.
        enabled: Whether the flag is on.
        updated_at: When the stored value last changed, UTC.
        updated_by_user_id: User id of that last write.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "A named boolean flag, when it last changed, and which user last wrote it."
            ),
        }
    )

    name: str = Field(
        min_length=1,
        description="Identifier of the flag within the caller's tenant.",
        examples=["dark_mode"],
    )
    enabled: bool = Field(
        description="Whether the flag is on.",
        examples=[True],
    )
    updated_at: datetime = Field(
        description="When the stored value last changed, UTC.",
        examples=["2026-01-15T12:00:00Z"],
    )
    updated_by_user_id: str = Field(
        min_length=1,
        description="User id of the last write.",
        examples=["user-1"],
    )
