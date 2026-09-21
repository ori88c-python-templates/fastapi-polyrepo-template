"""Shared types and helpers for the :class:`LogManager` tests.

Kept separate from ``conftest.py`` because fixtures are discovered by pytest while these are
imported by name, and importing from a conftest module is discouraged.
"""

import io
import json
from collections.abc import Callable
from typing import Any

from app.logger.log_manager import LogManager

ManagerFactory = Callable[..., LogManager]


def read_records(stream: io.BytesIO) -> list[dict[str, Any]]:
    """Parse everything written to ``stream`` as newline-delimited JSON.

    Args:
        stream: The buffer a manager has been writing to.

    Returns:
        One dict per emitted record, in the order they were written.

    Raises:
        UnicodeDecodeError: If the output is not valid UTF-8, which is itself a failure
            worth surfacing rather than hiding behind a replacement character.
    """
    text = stream.getvalue().decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line]
