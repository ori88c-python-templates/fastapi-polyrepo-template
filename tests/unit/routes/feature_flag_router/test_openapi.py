"""OpenAPI contract for the feature-flag routes."""

from http import HTTPStatus

from fastapi import FastAPI

_GET_PATH = "/api/v1/feature-flags/{name}"
_PUT_PATH = "/api/v1/feature-flags/{name}"


def test_get_openapi_does_not_leak_handler_internals(feature_flag_app: FastAPI) -> None:
    """Decorator copy is the public contract; Google Args for DI stay in the code."""
    operation = feature_flag_app.openapi()["paths"][_GET_PATH]["get"]
    description = operation.get("description", "")

    assert operation["summary"] == "Get a feature flag"
    assert operation["operationId"] == "getFeatureFlag"
    assert "Injected by FastAPI" not in description
    assert "Route-named child logger" not in description
    assert str(HTTPStatus.NOT_FOUND.value) in operation["responses"]


def test_put_openapi_does_not_leak_handler_internals(feature_flag_app: FastAPI) -> None:
    """PUT uses the same split: customer description, no logger or service Args."""
    operation = feature_flag_app.openapi()["paths"][_PUT_PATH]["put"]
    description = operation.get("description", "")

    assert operation["summary"] == "Set a feature flag"
    assert operation["operationId"] == "setFeatureFlag"
    assert "Injected by FastAPI" not in description
    assert "Route-named child logger" not in description


def test_feature_flag_schema_description_is_customer_facing(
    feature_flag_app: FastAPI,
) -> None:
    """Google class docstrings stay in code; OpenAPI gets the json_schema_extra copy."""
    schemas = feature_flag_app.openapi()["components"]["schemas"]
    flag = schemas["FeatureFlag"]["description"]
    request = schemas["FeatureFlagSetRequest"]["description"]

    assert flag == "A named boolean flag and when it last changed."
    assert "ORM" not in flag
    assert "Attributes" not in flag
    assert "The name is the path parameter, not a field in this body." in request
    assert "Attributes" not in request
    assert "silently rename" not in request
