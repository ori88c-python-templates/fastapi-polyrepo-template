"""LoggerConfig defaults and env-shaped fields."""

from app.config import LoggerConfig


def test_uvicorn_access_logs_default_to_enabled() -> None:
    """Omitted ``ENABLE_UVICORN_ACCESS_LOGS`` matches uvicorn's ``access_log=True``."""
    assert LoggerConfig().ENABLE_UVICORN_ACCESS_LOGS is True


def test_uvicorn_access_logs_can_be_disabled() -> None:
    """An explicit false is accepted so ``main`` can pass ``access_log=False``."""
    config = LoggerConfig(ENABLE_UVICORN_ACCESS_LOGS=False)
    assert config.ENABLE_UVICORN_ACCESS_LOGS is False
