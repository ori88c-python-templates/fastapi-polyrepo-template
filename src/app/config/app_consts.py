"""Immutable protocol constants that must not be overridden by the environment.

Header names, the request-state correlation id key, unprefixed infrastructure
paths, and the log ``app`` identity are a contract with callers (kubelet,
Prometheus, inbound tracing, observability). They are not deployment settings:
putting them in ``.env`` would invite a typo to break every probe, scrape, or
Grafana filter.
"""

from typing import Final

APP_NAME: Final = "fastapi-polyrepo-template"
REQUEST_ID_HEADER: Final = "X-Request-ID"
CORRELATION_ID_HEADER: Final = "X-Correlation-ID"
CORRELATION_ID_STATE_KEY: Final = "correlation_id"
METRICS_ENDPOINT: Final = "/metrics"
LIVEZ_ENDPOINT: Final = "/livez"
READYZ_ENDPOINT: Final = "/readyz"
SWAGGER_DOCS_ENDPOINT: Final = "/docs"
REDOC_ENDPOINT: Final = "/redoc"
