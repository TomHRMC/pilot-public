import uuid
from datetime import UTC, datetime

from pydantic import AwareDatetime
from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class StandardAuditMixin(SQLModel):
    """Provides standard tracking for mutable records.

    Note: updated_at uses sa_column_kwargs to avoid Column reuse errors across multiple models.
    The onupdate parameter automatically updates the timestamp on modifications.
    The DateTime(timezone=True) ensures TIMESTAMPTZ columns in the database.
    """

    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
    )
    updated_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    # Removed the strict foreign key constraints here:
    created_by: uuid.UUID | None = Field(default=None)
    updated_by: uuid.UUID | None = Field(default=None)


class AppendOnlyMixin(SQLModel):
    """Provides tracking for immutable/ledger records.

    Note: Using sa_type instead of sa_column in mixins to avoid Column reuse errors.
    """

    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
    )
    # Removed the strict foreign key constraint here:
    created_by: uuid.UUID | None = Field(default=None)


class MachineLogMixin(SQLModel):
    """Provides minimal tracking for automated system events.

    Note: Using sa_type instead of sa_column in mixins to avoid Column reuse errors.
    """

    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
    )
