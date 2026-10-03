"""Service-layer errors for feature-flag reads and writes."""

from typing import Final


class FeatureFlagNotFoundError(Exception):
    """Raised when ``get_flag`` is asked for a name this tenant does not store.

    A service-layer error, not an HTTP one: routes translate it into a 404.
    A row for the same name under another tenant is still missing. Carrying
    the name lets the handler log and respond without parsing a message.

    Attributes:
        name: The flag that was requested.
    """

    def __init__(self, name: str) -> None:
        """Record which flag was missing.

        Args:
            name: The identifier that was looked up and not found.
        """
        self.name: Final = name
        super().__init__(f"Feature flag {name!r} does not exist.")
