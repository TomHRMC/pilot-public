"""
Marketing models — unauthenticated public form submissions.

MKT-B1-BE:  MarketingWaitlistSignup   (§6.1)
MKT-B1.5-BE: MarketingContactSubmission (§6.5)
MKT-B1.5-BE: MarketingNewsletterSubscriber (§6.6)

IMPORTANT: None of these models use StandardAuditMixin, AppendOnlyMixin, or
MachineLogMixin. All three mixins add a `created_by FK → user.id` which is
incompatible with public unauthenticated forms (no auth context).
"""

import uuid

from pydantic import AwareDatetime
from sqlalchemy import Boolean, DateTime, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel


class MarketingWaitlistSignup(SQLModel, table=True):
    """
    Public waitlist signup form submissions from the marketing site.
    No auth context — created by unauthenticated visitors at pilotfortrades.com.
    Email is case-insensitive unique via CITEXT PostgreSQL extension.
    """

    __tablename__ = "marketing_waitlist_signup"
    __table_args__ = (
        UniqueConstraint("email", name="uq_marketing_waitlist_signup_email"),
        Index("ix_marketing_waitlist_signup_email", "email"),
        Index("ix_marketing_waitlist_signup_created_at", "created_at"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    # CITEXT — stored as citext in the DB for case-insensitive uniqueness.
    # ORM uses String; the migration creates the column as CITEXT.
    email: str = Field(
        sa_column=Column(String, nullable=False),
    )
    name: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    trade: str = Field(
        sa_column=Column(String, nullable=False),
    )
    company_size: str = Field(
        sa_column=Column(String, nullable=False),
    )
    state: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    notes: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    source: str = Field(
        sa_column=Column(String, nullable=False),
    )
    utm_source: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    utm_medium: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    utm_campaign: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    created_at: AwareDatetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
    )
    converted_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )


class MarketingContactSubmission(SQLModel, table=True):
    """
    Contact form submissions from the marketing site (§6.5).
    No auth context. All submissions are stored for inbox tracking (info@).
    """

    __tablename__ = "marketing_contact_submission"
    __table_args__ = (
        Index("ix_marketing_contact_submission_email", "email"),
        Index("ix_marketing_contact_submission_created_at", "created_at"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    name: str = Field(
        sa_column=Column(String, nullable=False),
    )
    # CITEXT in DB; ORM uses String per B1 pattern
    email: str = Field(
        sa_column=Column(String, nullable=False),
    )
    company: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    trade: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    subject: str = Field(
        sa_column=Column(String, nullable=False),
    )
    message: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    source_page: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    created_at: AwareDatetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
    )
    is_read: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )


class MarketingNewsletterSubscriber(SQLModel, table=True):
    """
    Newsletter subscribers from the marketing site footer / blog CTAs (§6.6).
    Distinct from waitlist — these are content subscribers, not product early-access.
    UNIQUE on email (CITEXT). Supports one-click unsubscribe via signed token.
    """

    __tablename__ = "marketing_newsletter_subscriber"
    __table_args__ = (
        UniqueConstraint("email", name="uq_marketing_newsletter_subscriber_email"),
        Index("ix_marketing_newsletter_subscriber_email", "email"),
        Index("ix_marketing_newsletter_subscriber_subscribed_at", "subscribed_at"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    # CITEXT in DB; ORM uses String per B1 pattern
    email: str = Field(
        sa_column=Column(String, nullable=False),
    )
    # PostgreSQL ARRAY(VARCHAR) — SQLModel doesn't natively support ARRAY;
    # must use explicit sa_column with postgresql.ARRAY(String).
    trade_interest: list[str] | None = Field(
        default=None,
        sa_column=Column(PG_ARRAY(String), nullable=True),
    )
    content_preferences: list[str] | None = Field(
        default=None,
        sa_column=Column(PG_ARRAY(String), nullable=True),
    )
    source: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    utm_source: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    utm_medium: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    utm_campaign: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    subscribed_at: AwareDatetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
    )
    unsubscribed_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )


class MarketingJobApplication(SQLModel, table=True):
    """
    Job application form submissions from the marketing careers page.
    No auth context. All applications stored for careers@ inbox tracking.
    """

    __tablename__ = "marketing_job_application"
    __table_args__ = (
        Index("ix_marketing_job_application_email", "email"),
        Index("ix_marketing_job_application_created_at", "created_at"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    )
    name: str = Field(sa_column=Column(String, nullable=False))
    email: str = Field(sa_column=Column(String, nullable=False))
    role: str = Field(sa_column=Column(String, nullable=False))
    linkedin_url: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    portfolio_url: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    why_interested: str = Field(sa_column=Column(Text, nullable=False))
    created_at: AwareDatetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        ),
    )
    is_reviewed: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
