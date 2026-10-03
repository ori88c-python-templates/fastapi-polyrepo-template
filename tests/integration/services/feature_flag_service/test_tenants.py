"""The same flag name is a different row for each tenant."""

import pytest

from app.models.user_details import UserDetails
from app.services import FeatureFlagNotFoundError, FeatureFlagService

_NAME = "dark_mode"
_TENANT_A = UserDetails(tenant_id="tenant-a", user_id="user-1")
_TENANT_B = UserDetails(tenant_id="tenant-b", user_id="user-2")


async def test_the_same_name_is_a_different_flag_per_tenant(
    feature_flag_service: FeatureFlagService,
) -> None:
    """Two tenants can store one name with different values and editors."""
    await feature_flag_service.set_flag(_NAME, enabled=True, user_details=_TENANT_A)
    await feature_flag_service.set_flag(_NAME, enabled=False, user_details=_TENANT_B)

    loaded_a = await feature_flag_service.get_flag(_NAME, _TENANT_A)
    loaded_b = await feature_flag_service.get_flag(_NAME, _TENANT_B)

    assert loaded_a.enabled is True
    assert loaded_a.updated_by_user_id == _TENANT_A.user_id
    assert loaded_b.enabled is False
    assert loaded_b.updated_by_user_id == _TENANT_B.user_id


async def test_get_for_another_tenant_is_not_found(
    feature_flag_service: FeatureFlagService,
) -> None:
    """A row for tenant A is missing when tenant B asks for the same name."""
    await feature_flag_service.set_flag(_NAME, enabled=True, user_details=_TENANT_A)

    with pytest.raises(FeatureFlagNotFoundError) as caught:
        await feature_flag_service.get_flag(_NAME, _TENANT_B)

    assert caught.value.name == _NAME
