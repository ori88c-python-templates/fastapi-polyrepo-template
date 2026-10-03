"""OpenAPI contract for the feature-flag routes."""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI

from app.config import TENANT_ID_HEADER, USER_ID_HEADER

_GET_PATH = "/api/v1/feature-flags/{name}"
_PUT_PATH = "/api/v1/feature-flags/{name}"
_GET_DESCRIPTION = (
    "Return the current value of a named flag for the tenant in the X-Tenant-ID header, "
    "including when it last changed and which user last wrote it."
)
_PUT_DESCRIPTION = (
    "Create or update a named flag for the tenant in the X-Tenant-ID header. "
    "The writing user is taken from X-User-ID and stored as the last editor. "
    "The name is taken from the path so the body cannot rename the resource."
)
_HEADER_DESCRIPTIONS = {
    TENANT_ID_HEADER: "Tenant this flag belongs to.",
    USER_ID_HEADER: "User performing this call. A write is recorded as the last editor.",
}


def _header(operation: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the single header parameter named ``name``.

    Args:
        operation: One OpenAPI operation object.
        name: Header name, such as ``X-Tenant-ID``.

    Returns:
        The matching parameter object.
    """
    matches = [
        parameter
        for parameter in operation["parameters"]
        if parameter["in"] == "header" and parameter["name"] == name
    ]
    (found,) = matches
    return found


def test_get_openapi_does_not_leak_handler_internals(feature_flag_app: FastAPI) -> None:
    """Decorator copy is the public contract; Google Args for DI stay in the code."""
    operation = feature_flag_app.openapi()["paths"][_GET_PATH]["get"]
    description = operation.get("description", "")

    assert operation["summary"] == "Get a feature flag"
    assert operation["operationId"] == "getFeatureFlag"
    assert description == _GET_DESCRIPTION
    assert "Injected by FastAPI" not in description
    assert "Route-named child logger" not in description
    assert str(HTTPStatus.NOT_FOUND.value) in operation["responses"]
    for name, header_description in _HEADER_DESCRIPTIONS.items():
        header = _header(operation, name)
        assert header["required"] is True
        assert header["description"] == header_description


def test_put_openapi_does_not_leak_handler_internals(feature_flag_app: FastAPI) -> None:
    """PUT uses the same split: customer description, no logger or service Args."""
    operation = feature_flag_app.openapi()["paths"][_PUT_PATH]["put"]
    description = operation.get("description", "")

    assert operation["summary"] == "Set a feature flag"
    assert operation["operationId"] == "setFeatureFlag"
    assert description == _PUT_DESCRIPTION
    assert "Injected by FastAPI" not in description
    assert "Route-named child logger" not in description
    for name, header_description in _HEADER_DESCRIPTIONS.items():
        header = _header(operation, name)
        assert header["required"] is True
        assert header["description"] == header_description


def test_feature_flag_schema_description_is_customer_facing(
    feature_flag_app: FastAPI,
) -> None:
    """Google class docstrings stay in code; OpenAPI gets the json_schema_extra copy."""
    schemas = feature_flag_app.openapi()["components"]["schemas"]
    flag = schemas["FeatureFlag"]["description"]
    request = schemas["FeatureFlagSetRequest"]["description"]
    editor = schemas["FeatureFlag"]["properties"]["updated_by_user_id"]

    assert flag == ("A named boolean flag, when it last changed, and which user last wrote it.")
    assert "ORM" not in flag
    assert "Attributes" not in flag
    assert editor["description"] == "User id of the last write."
    assert "The name is the path parameter, not a field in this body." in request
    assert "Attributes" not in request
    assert "silently rename" not in request
