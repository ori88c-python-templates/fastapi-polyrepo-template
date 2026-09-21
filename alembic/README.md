# alembic

Alembic lives next to the application, not inside it.

- `env.py` builds a migration-owned engine from `POSTGRES__*` and `PostgresBase.metadata`.
- That engine takes `POSTGRES__CONNECT_TIMEOUT_SECONDS` and not
  `POSTGRES__STATEMENT_TIMEOUT_MS`.
- Revisions live in `versions/`. Review autogenerate output before committing.
- Apply with `uv run alembic upgrade head`. Do not run this from the HTTP process.

See the root README for the local loop and the Job-then-Deployment contract.
