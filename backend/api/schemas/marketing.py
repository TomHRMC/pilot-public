"""
Marketing API Pydantic schemas.

MKT-B1-BE:  WaitlistSignupRequest, WaitlistSignupResponse
MKT-B1.5-BE: ContactSubmissionRequest, ContactSubmissionResponse
             NewsletterSubscribeRequest, NewsletterSubscribeResponse
             NewsletterUnsubscribeResponse
MKT-B6:     JobApplicationRequest, JobApplicationResponse

A-11 (2026-06-27): Added email TLD field_validator to all 4 request schemas.
    Pydantic's EmailStr (email-validator 2.x) does not enforce minimum TLD length.
    This validator adds that check: TLD must be at least 2 chars.
    Catches me@me.t which EmailStr accepts but is clearly junk.
"""

import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

# ---------------------------------------------------------------------------
# Shared email TLD validator — applied to all 4 request schemas with email
# ---------------------------------------------------------------------------

_EMAIL_TLD_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def _validate_email_tld(v: str) -> str:
    """TLD must be at least 2 characters. Rejects me@me.t etc."""
    if not _EMAIL_TLD_RE.match(v):
        raise ValueError("Enter a valid email address (e.g. name@example.com)")
    return v.lower()


# ─── Waitlist (B1) ───────────────────────────────────────────────────────────


class WaitlistSignupRequest(BaseModel):
    """
    Public waitlist form submission from pilotfortrades.com.

    Fields:
        email: Subscriber's email address (case-insensitive — stored as CITEXT).
        trade: Trade vertical the subscriber works in.
        company_size: Rough crew size bucket.
        source: Page/section where the form was submitted (e.g. "homepage_hero").
        utm_source/medium/campaign: Optional UTM attribution parameters.
        cf_turnstile_response: Cloudflare Turnstile token from the browser widget.
        honeypot: Hidden field — must be empty on legitimate submissions.
                  If non-empty, the request is rejected as a bot.
                  This field is NEVER stored to the database.
    """

    email: EmailStr
    name: str | None = None
    trade: Literal["electrical", "plumbing", "hvac", "other"]
    company_size: Literal["solo", "2-5", "6-10", "10+"]
    state: str | None = None
    notes: str | None = None
    source: str
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    cf_turnstile_response: str
    honeypot: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_tld(cls, v: str) -> str:
        return _validate_email_tld(v)


class WaitlistSignupResponse(BaseModel):
    """
    Success response for waitlist signup.

    Returned on both 201 (new signup) and 200 (duplicate email — idempotent).
    The same shape is always returned to prevent email enumeration attacks.
    """

    status: str
    message: str
    position: int


# ─── Contact Form (B1.5) ─────────────────────────────────────────────────────


class ContactSubmissionRequest(BaseModel):
    """
    Contact form submission from the marketing site (§6.5).
    Honeypot and Turnstile fields are checked server-side; never stored.
    """

    name: str
    email: EmailStr
    company: str | None = None
    trade: Literal["electrical", "plumbing", "hvac", "other"] | None = None
    subject: str
    message: str = Field(..., max_length=5000)
    source_page: str | None = None
    cf_turnstile_response: str
    honeypot: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_tld(cls, v: str) -> str:
        return _validate_email_tld(v)


class ContactSubmissionResponse(BaseModel):
    """Success response for contact form submission."""

    status: str
    message: str


# ─── Newsletter (B1.5) ───────────────────────────────────────────────────────


class NewsletterSubscribeRequest(BaseModel):
    """
    Newsletter subscribe form from the marketing site footer / blog CTAs (§6.6).
    Distinct from the waitlist — content subscribers, not product early-access.
    Honeypot and Turnstile fields are checked server-side; never stored.
    """

    email: EmailStr
    trade_interest: list[str] | None = None
    content_preferences: list[str] | None = None
    source: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    cf_turnstile_response: str
    honeypot: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_tld(cls, v: str) -> str:
        return _validate_email_tld(v)


class NewsletterSubscribeResponse(BaseModel):
    """
    Success response for newsletter subscribe.
    Returned on both 201 (new subscriber) and 200 (duplicate — idempotent).
    Same shape always to prevent email enumeration.
    """

    status: str
    message: str


class NewsletterUnsubscribeResponse(BaseModel):
    """Success response for newsletter unsubscribe (always 200 — idempotent)."""

    status: str
    message: str


# ─── Job Application (MKT-B6) ────────────────────────────────────────────────


class JobApplicationRequest(BaseModel):
    """
    Job application form submission from the marketing careers page.
    Honeypot and Turnstile fields are checked server-side; never stored.
    """

    name: str
    email: EmailStr
    role: str = Field(..., max_length=200)
    linkedin_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    why_interested: str = Field(..., max_length=2000)
    cf_turnstile_response: str
    honeypot: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_tld(cls, v: str) -> str:
        return _validate_email_tld(v)


class JobApplicationResponse(BaseModel):
    """Success response for job application submission."""

    status: str
    message: str
