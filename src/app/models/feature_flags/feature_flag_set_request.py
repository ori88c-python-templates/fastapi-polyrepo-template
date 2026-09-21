"""Body of a request that turns a feature flag on or off."""

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlagSetRequest(BaseModel):
    """The value to persist for a named flag.

    The flag's name is the path parameter, not a field here, so a PUT cannot
    silently rename the resource it is addressing.

    Attributes:
        enabled: The value to persist.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "The value to persist for a named flag. The name is the path "
                "parameter, not a field in this body."
            ),
        }
    )

    enabled: bool = Field(
        description="The value to persist.",
        examples=[True],
    )
