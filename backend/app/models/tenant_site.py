"""TenantSite SQLModel — C-B16 Part A.

Pilot-hosted tenant compliance sites (SMS compliance pages + compliance kit).
Single row per tenant (UNIQUE on tenant_id). Publish → snapshot → SSR serve.

Design: dev-docs/architecture-design/batch-designs/batch-c-b16-design.md §B.1
"""

import uuid

from pydantic import AwareDatetime
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .mixins import StandardAuditMixin


class TenantSite(StandardAuditMixin, SQLModel, table=True):
    """Tenant compliance site configuration (1:1 per tenant).

    site_kind:
        'compliance_kit'    — tenant self-hosts; Pilot sends requirements email + guide.
        'hosted_compliance' — Pilot hosts a 3-page site (landing + privacy + terms).
        'starter_site'      — reserved for C-B17 (CHECK constraint excludes it for now).

    status:
        'draft'      — configured but not published.
        'published'  — snapshot rendered and live; public endpoint serves it.
        'unpublished'— retracted; public endpoint returns 404 (website NOT cleared).
    """

    __tablename__ = "tenant_site"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
    slug: str = Field(max_length=63)
    site_kind: str = Field(max_length=20)
    status: str = Field(default="draft", max_length=20)
    display_name: str = Field(max_length=200)
    tagline: str | None = Field(default=None, max_length=300)
    public_email: str | None = Field(default=None, max_length=320)
    public_phone: str | None = Field(default=None, max_length=32)
    public_city: str | None = Field(default=None, max_length=120)
    public_state: str | None = Field(default=None, max_length=2)
    public_address_line1: str | None = Field(default=None, max_length=200)
    public_postal_code: str | None = Field(default=None, max_length=10)
    show_full_address: bool = Field(default=False)
    template_version: str = Field(default="v1", max_length=20)
    published_snapshot: dict | None = Field(default=None, sa_column=Column(JSONB))
    published_at: AwareDatetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    unpublished_at: AwareDatetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    kit_sent_at: AwareDatetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    website_auto_populated: bool = Field(default=False)
    idempotency_key: str | None = Field(default=None, max_length=100)
