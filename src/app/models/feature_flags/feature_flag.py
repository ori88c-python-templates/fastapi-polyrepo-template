"""The feature flag as the API and service layer speak it."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlag(BaseModel):
    """A named boolean flag and when it last changed.

    Distinct from the ORM row: this model uses ``enabled`` where the table uses
    ``value``, so a column rename is not automatically a breaking API change.

    Attributes:
        name: Unique identifier of the flag.
        enabled: Whether the flag is on.
        updated_at: When the stored value last changed, UTC.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "A named boolean flag and when it last changed.",
        }
    )

    name: str = Field(
        min_length=1,
        description="Unique identifier of the flag.",
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
