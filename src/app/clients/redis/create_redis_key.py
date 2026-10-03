"""Build a Redis key whose parts cannot collide across a colon."""


def create_redis_key(prefix: str, *parts: str) -> str:
    """Build a Redis key from ``prefix`` and ``parts``.

    Each part is written as ``len(part):part``. The pieces are joined with
    ``:``. The length keeps a colon inside a part from merging with the next
    part. ``create_redis_key("feature_flag", "a", "b:c")`` is
    ``feature_flag:1:a:3:b:c``. ``create_redis_key("feature_flag", "a:b", "c")``
    is ``feature_flag:3:a:b:1:c``. Without the lengths both would be
    ``feature_flag:a:b:c``.

    Args:
        prefix: Leading namespace. It is not length-prefixed.
        *parts: Key segments. A caller converts a non-string before the call.

    Returns:
        The joined key.
    """
    pieces = [prefix]
    for part in parts:
        pieces.append(str(len(part)))
        pieces.append(part)
    return ":".join(pieces)
