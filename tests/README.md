# tests

The test suite, split by how much of the real world a test is allowed to touch.

| Path | What belongs there |
| --- | --- |
| [`unit/`](unit/README.md) | In-process tests. Dependencies are injected (buffers, temp files, `AsyncMock`). |
| [`integration/`](integration/README.md) | A service against real Redis and PostgreSQL via Testcontainers. |
| [`e2e/`](e2e/README.md) | HTTP through the real application against Testcontainers. |

Within each tree, layout mirrors `src/app/`: one directory per package, then one
directory per component under test, then one file per feature.

## Running

```bash
uv run pytest
uv run pytest -v
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e
```

`testpaths` in `pyproject.toml` lists `tests/unit`, then `tests/integration`, then `tests/e2e`, so a bare `uv run pytest` collects in that order. Integration and e2e
need Docker Desktop; those tests skip if the daemon is down. `uv run pytest tests/unit` never starts
a container.

Conventions are defined in [.cursor/rules/tests.mdc](../.cursor/rules/tests.mdc).
