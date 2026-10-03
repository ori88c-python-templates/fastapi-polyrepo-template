"""Header builder for feature-flag HTTP tests.

Kept out of ``conftest.py`` because fixtures are discovered by pytest while this
is imported by name, and importing from a conftest module is discouraged.
"""

from app.config import TENANT_ID_HEADER, USER_ID_HEADER


def caller_headers(tenant_id: str = "tenant-a", user_id: str = "user-1") -> dict[str, str]:
    """Build the caller headers feature-flag requests require.

    Args:
        tenant_id: Value for ``X-Tenant-ID``.
        user_id: Value for ``X-User-ID``.

    Returns:
        Headers for one caller.
    """
    return {TENANT_ID_HEADER: tenant_id, USER_ID_HEADER: user_id}
