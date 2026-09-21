"""Configuration for the feature-flag service."""

from pydantic import BaseModel, Field


class FeatureFlagConfig(BaseModel):
    """Settings for feature-flag reads and the Redis cache in front of them.

    Attributes:
        CACHE_TTL_SECONDS: How long a flag stays in Redis after a database load
            or a write. Defaults to three hundred (five minutes). Values below
            one are rejected because Redis ``SET EX`` takes an integer number of
            seconds, and zero would mean "no expiry".
    """

    CACHE_TTL_SECONDS: int = Field(default=300, ge=1)
