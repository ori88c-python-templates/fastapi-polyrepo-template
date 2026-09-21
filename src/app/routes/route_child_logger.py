"""FastAPI dependency that injects a child logger named after the matched route."""

from typing import Annotated

from fastapi import Depends, Request
from structlog.typing import FilteringBoundLogger

from app.state import get_app_state


def get_route_logger(request: Request) -> FilteringBoundLogger:
    """Return a child logger whose ``context`` is the matched route's name.

    ``Depends`` only runs after FastAPI has matched a path operation, so
    ``scope["route"]`` is the ``APIRoute``. Give that route an explicit ``name=``
    on the decorator; FastAPI's generated name follows the function name and
    would churn whenever a handler is renamed.

    Args:
        request: The in-flight request. Used to reach both the matched route and
            the process-wide ``LogManager`` on application state.

    Returns:
        A logger from that ``LogManager``. The correlation id is not bound here:
        ``CorrelationIdMiddleware`` already put it in structlog's contextvars,
        and every child logger on this request picks it up.
    """
    route = request.scope["route"]
    return get_app_state(request).log_manager.get_child_logger(route.name)


RouteLogger = Annotated[FilteringBoundLogger, Depends(get_route_logger)]
