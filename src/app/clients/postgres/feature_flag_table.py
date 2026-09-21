"""ORM mapping for the ``feature_flags`` table."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.clients.postgres.postgres_base import PostgresBase


class FeatureFlagRow(PostgresBase):
    """Persistence schema for a named boolean flag.

    This is not an API model. The column is ``value``; the service layer exposes
    the same bit as ``enabled`` so a rename of either side is not automatically
    a breaking change on the other.

    Attributes:
        name: Primary key. Unique flag identifier.
        value: Stored boolean.
        updated_at: Last write time, timezone-aware.
    """

    __tablename__ = "feature_flags"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
