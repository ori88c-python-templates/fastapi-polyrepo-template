"""Declarative base for every PostgreSQL ORM mapping in this application."""

from sqlalchemy.orm import DeclarativeBase


class PostgresBase(DeclarativeBase):
    """Shared SQLAlchemy registry for PostgreSQL tables.

    One base so metadata and mappings stay in a single catalog. Production never
    calls ``create_all``; schema changes are applied out of band with Alembic
    (``alembic upgrade head``), not by this process.
    """
