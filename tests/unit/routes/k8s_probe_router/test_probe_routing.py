"""The routing contract kubelet is configured against."""

from http import HTTPStatus

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import LIVEZ_ENDPOINT, READYZ_ENDPOINT

PROBE_PATHS = [LIVEZ_ENDPOINT, READYZ_ENDPOINT]


async def test_liveness_is_served_without_an_api_prefix(probe_client: AsyncClient) -> None:
    """Liveness is exactly the path a manifest configures, with nothing in front.

    A prefix would couple kubelet's configuration to the API version, so bumping to
    ``/api/v2`` would silently stop every probe and roll the deployment.
    """
    response = await probe_client.get(LIVEZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK


async def test_readiness_is_served_without_an_api_prefix(ready_client: AsyncClient) -> None:
    """Readiness is exactly the path a manifest configures, with nothing in front."""
    response = await ready_client.get(READYZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize("path", PROBE_PATHS)
async def test_probes_are_not_reachable_under_an_api_prefix(
    probe_client: AsyncClient, path: str
) -> None:
    """Nothing answers on a prefixed path, so the unprefixed one is not an alias."""
    response = await probe_client.get(f"/api/v1{path}")

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("path", PROBE_PATHS)
async def test_probes_reject_methods_other_than_get(probe_client: AsyncClient, path: str) -> None:
    """Probes are reads. Anything else is a misconfiguration worth surfacing."""
    response = await probe_client.post(path)

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


@pytest.mark.parametrize("path", PROBE_PATHS)
def test_probes_are_documented_in_the_openapi_schema(probe_app: FastAPI, path: str) -> None:
    """Both probes appear in the schema under one tag, so they group in the docs."""
    schema = probe_app.openapi()

    assert schema["paths"][path]["get"]["tags"] == ["probes"]


@pytest.mark.parametrize("path", PROBE_PATHS)
def test_probes_document_their_success_body(probe_app: FastAPI, path: str) -> None:
    """A 200 is declared as returning JSON, not an untyped or empty response."""
    schema = probe_app.openapi()
    responses = schema["paths"][path]["get"]["responses"]

    assert "application/json" in responses[str(HTTPStatus.OK.value)]["content"]


def test_probe_openapi_uses_decorator_copy_not_the_handler_docstring(
    probe_app: FastAPI,
) -> None:
    """Kubelet crash-loop rationale stays in the code docstring, not in Swagger."""
    schema = probe_app.openapi()
    liveness = schema["paths"][LIVEZ_ENDPOINT]["get"]
    readiness = schema["paths"][READYZ_ENDPOINT]["get"]

    assert liveness["summary"] == "Liveness probe"
    assert liveness["operationId"] == "livenessProbe"
    assert "crash-loop" not in liveness.get("description", "")
    assert readiness["summary"] == "Readiness probe"
    assert readiness["operationId"] == "readinessProbe"
    assert str(HTTPStatus.SERVICE_UNAVAILABLE.value) in readiness["responses"]


def test_probe_schema_description_is_customer_facing(probe_app: FastAPI) -> None:
    """Implementation notes about dicts and OpenAPI stay in the class docstring."""
    description = probe_app.openapi()["components"]["schemas"]["K8sProbeResponse"]["description"]

    assert "bare dict" not in description
    assert "OpenAPI schema" not in description
    assert description.startswith("Body of a successful probe.")


async def test_probes_hidden_from_schema_are_still_served(
    schema_hidden_probe_app: FastAPI,
) -> None:
    """Staging and production omit kubelet paths from OpenAPI; kubelet still calls them."""
    schema = schema_hidden_probe_app.openapi()
    paths = schema.get("paths", {})
    for path in PROBE_PATHS:
        assert path not in paths

    async with AsyncClient(
        transport=ASGITransport(app=schema_hidden_probe_app),
        base_url="http://probes.test",
    ) as client:
        for path in PROBE_PATHS:
            response = await client.get(path)
            assert response.status_code == HTTPStatus.OK
