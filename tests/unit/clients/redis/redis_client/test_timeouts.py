"""RedisClient passes connect and command timeouts into redis-py."""

from app.clients import RedisClient
from app.config import RedisConfig
from app.logger import LogManager


def test_from_url_receives_socket_timeouts(log_manager: LogManager) -> None:
    """Construction is lazy: inspecting the pool does not open a socket."""
    config = RedisConfig(
        HOST="127.0.0.1",
        CONNECT_TIMEOUT_SECONDS=3,
        COMMAND_TIMEOUT_SECONDS=7,
    )
    client = RedisClient(config, log_manager.get_child_logger("RedisClient"))
    kwargs = client.raw.connection_pool.connection_kwargs
    assert kwargs["socket_connect_timeout"] == 3
    assert kwargs["socket_timeout"] == 7
    assert kwargs["retry_on_timeout"] is False
