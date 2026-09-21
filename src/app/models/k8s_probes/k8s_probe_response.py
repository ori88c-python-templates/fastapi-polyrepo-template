"""Response body returned by the Kubernetes probe endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class K8sProbeResponse(BaseModel):
    """The body of a successful probe.

    A probe is judged by its status code, not its body, so this exists mainly to give
    the endpoints an honest OpenAPI schema. Keeping it a model rather than a bare dict
    also means a future field, such as a version or a per-dependency breakdown, is an
    additive change.

    Attributes:
        status: Always ``"ok"``. A failing probe returns a non-2xx status code instead
            of this body, so there is no failure value to represent.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "Body of a successful probe. Failures use a non-2xx status instead of this schema."
            ),
        }
    )

    status: Literal["ok"] = Field(
        default="ok",
        description="Always ok. A failing probe uses a non-2xx status instead of this body.",
    )
