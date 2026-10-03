"""ORM mapping for the ``feature_flags`` table."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.clients.postgres.postgres_base import PostgresBase


class FeatureFlagRow(PostgresBase):
    """Persistence schema for a boolean flag belonging to one tenant.

    This is not an API model. The column is ``value``; the service layer exposes
    the same bit as ``enabled`` so a rename of either side is not automatically
    a breaking change on the other. ``tenant_id`` and ``name`` are one composite
    primary key, not two independent keys: two tenants may store the same name
    with different values, and a second row with the same pair is rejected.

    Attributes:
        tenant_id: Tenant the flag belongs to. Part of the composite primary key.
        name: Flag identifier within that tenant. Part of the composite primary key.
        value: Stored boolean.
        updated_at: Last write time, timezone-aware.
        updated_by_user_id: User id of that last write.
    """

    __tablename__ = "feature_flags"

    tenant_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by_user_id: Mapped[str] = mapped_column(Text, nullable=False)
