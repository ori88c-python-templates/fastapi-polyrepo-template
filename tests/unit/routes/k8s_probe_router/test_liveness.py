"""The liveness probe: what it answers, and what it refuses to depend on."""

from http import HTTPStatus

from httpx import AsyncClient

from app.config import LIVEZ_ENDPOINT


async def test_liveness_returns_ok(probe_client: AsyncClient) -> None:
    """A running process reports itself alive."""
    response = await probe_client.get(LIVEZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK


async def test_liveness_body_reports_ok(probe_client: AsyncClient) -> None:
    """The body matches the documented schema exactly, with no extra keys."""
    response = await probe_client.get(LIVEZ_ENDPOINT)

    assert response.json() == {"status": "ok"}


async def test_liveness_answers_on_an_application_that_was_never_started(
    probe_client: AsyncClient,
) -> None:
    """Liveness holds without config, state, clients, or a lifespan having run.

    This is the guarantee that matters. Liveness failing restarts the pod, and a restart
    cannot repair an external dependency, so a liveness check that reaches for one turns
    a dependency blip into a fleet-wide crash-loop. The client's transport never runs the
    lifespan and the app carries no state, so a handler touching either would fail here.
    """
    response = await probe_client.get(LIVEZ_ENDPOINT)

    assert response.status_code == HTTPStatus.OK


async def test_liveness_is_repeatable(probe_client: AsyncClient) -> None:
    """Probing on an interval, as kubelet does, keeps returning the same answer."""
    responses = [await probe_client.get(LIVEZ_ENDPOINT) for _ in range(3)]

    assert [response.status_code for response in responses] == [HTTPStatus.OK] * 3
