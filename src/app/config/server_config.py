"""Configuration for the HTTP server the application binds to."""

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Bind address of the HTTP server.

    Attributes:
        HOST: Interface to bind to. Defaults to ``0.0.0.0`` so the process is
            reachable from outside its container.
        PORT: TCP port to listen on. Constrained to the valid port range.
    """

    # S104: binding to all interfaces is required, not accidental. A container's service has to
    # be reachable from outside its network namespace; exposure is controlled at the network layer.
    HOST: str = Field(default="0.0.0.0", min_length=1)  # noqa: S104
    PORT: int = Field(default=8080, ge=1, le=65535)
