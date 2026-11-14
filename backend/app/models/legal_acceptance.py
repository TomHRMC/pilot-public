"""
B14/A74 — Legal Acceptance Recording model.
Table: tenant_legal_acceptance
Mixin: AppendOnlyMixin — immutable; modifying acceptance records would undermine legal enforceability.
"""

import uuid

from pydantic import AwareDatetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin


class TenantLegalAcceptance(AppendOnlyMixin, SQLModel, table=True):
    """
    Immutable record of a user accepting a legal document.
    document_type: tos | privacy | eula | marketing_email_optin
    """

    __tablename__ = "tenant_legal_acceptance"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('tos', 'privacy', 'eula', 'marketing_email_optin')",
            name="tenant_legal_acceptance_document_type_chk",
        ),
    )

    acceptance_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    tenant_id: uuid.UUID = Field(
        foreign_key="tenant.id",
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    document_type: str = Field(
        sa_column=Column(String, nullable=False),
    )
    document_version_hash: str = Field(
        sa_column=Column(String, nullable=False),
    )
    accepted_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    ip_address: str = Field(
        sa_column=Column(INET, nullable=False),
    )
    user_agent: str = Field(
        sa_column=Column(String, nullable=False),
    )

    # AppendOnlyMixin provides created_at + created_by
    # Phase 6.0.1 pattern: Override created_by with FK constraint
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
