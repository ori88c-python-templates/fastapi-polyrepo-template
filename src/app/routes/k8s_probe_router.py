"""Kubernetes liveness and readiness probes.

Deliberately unprefixed. Probes are infrastructure rather than API surface: kubelet is
configured with these paths in a manifest, and versioning the API must never require a
deployment change. An exact, unprefixed path is also the easiest thing to exempt from
authentication middleware later.
"""

from typing import Final

from fastapi import APIRouter, HTTPException, Request, status

from app.config import LIVEZ_ENDPOINT, READYZ_ENDPOINT
from app.models.k8s_probes import K8sProbeResponse
from app.state import get_app_state

k8s_probe_router: Final = APIRouter(tags=["probes"])


@k8s_probe_router.get(
    LIVEZ_ENDPOINT,
    operation_id="livenessProbe",
    summary="Liveness probe",
    description="Report whether the process can serve at all. Does not check Redis or PostgreSQL.",
    status_code=status.HTTP_200_OK,
)
async def liveness_probe() -> K8sProbeResponse:
    """Report whether the process is still able to serve at all.

    Never check an external resource here, and never add one later. Failing this probe
    makes kubelet kill and restart the container, and a restart cannot fix a Redis or
    PostgreSQL outage. Checking dependencies here turns a partial outage into a
    fleet-wide crash-loop, taking down every pod at once and hammering the dependency
    with reconnects exactly when it is least able to cope.

    The only honest failure for liveness is a process that can no longer recover on its
    own: a wedged event loop, a deadlock, exhausted memory. Returning at all already
    demonstrates the event loop is scheduling work.

    Returns:
        A 200 response for as long as the process is running.
    """
    return K8sProbeResponse()


@k8s_probe_router.get(
    READYZ_ENDPOINT,
    operation_id="readinessProbe",
    summary="Readiness probe",
    description=(
        "Report whether this instance can currently serve traffic. Returns 503 if Redis "
        "or PostgreSQL does not answer."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Redis or PostgreSQL failed a health check.",
        },
    },
)
async def readiness_probe(request: Request) -> K8sProbeResponse:
    """Report whether this instance can currently serve traffic.

    This is where dependency checks belong. Failing readiness removes the pod from the
    Service endpoints without killing it, so traffic is routed to healthy instances and
    returns automatically once the dependency recovers.

    Check only what a request genuinely cannot be served without, and check it cheaply:
    this runs on every probe interval, on every pod. A ``PING`` against an existing
    pooled connection, not a fresh connection or a real query.

    Args:
        request: Used only to reach the shared clients on application state.

    Returns:
        A 200 response when Redis and PostgreSQL both answer.

    Raises:
        HTTPException: 503 if either dependency fails its ping, so kubelet
            withholds traffic without restarting the pod. The ``detail`` names
            the resource that failed (Redis or PostgreSQL).
    """
    clients = get_app_state(request).clients
    try:
        await clients.redis.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis failed a health check.",
        ) from exc
    try:
        await clients.postgres.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL failed a health check.",
        ) from exc
    return K8sProbeResponse()
