"""
MKT-B1-BE + MKT-B1.5-BE — Marketing API routes.

Route registration order (§8.2: /test before public, specific before generic):
    POST /api/v1/marketing/waitlist/test
    POST /api/v1/marketing/waitlist
    POST /api/v1/marketing/contact/test
    POST /api/v1/marketing/contact
    POST /api/v1/marketing/newsletter/test
    POST /api/v1/marketing/newsletter/unsubscribe  ← registered BEFORE /newsletter
    POST /api/v1/marketing/newsletter

Security model (all three public forms):
    1. CORS — pilotfortrades.com origin only
    2. Cloudflare Turnstile — bot proof
    3. Rate limiting — 10 req/IP/hour via SlowAPI
    4. Honeypot field + UNIQUE email (where applicable)

Email notifications use dedicated Celery tasks — no notification_outbox (tenant_id FK incompatible).
"""

import base64
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from api.schemas.marketing import (
    ContactSubmissionRequest,
    ContactSubmissionResponse,
    JobApplicationRequest,
    JobApplicationResponse,
    NewsletterSubscribeRequest,
    NewsletterSubscribeResponse,
    NewsletterUnsubscribeResponse,
    WaitlistSignupRequest,
    WaitlistSignupResponse,
)
from app.models.marketing import (
    MarketingContactSubmission,
    MarketingJobApplication,
    MarketingNewsletterSubscriber,
    MarketingWaitlistSignup,
)
from core.config import settings
from core.db import get_db
from core.rate_limit import limiter
from core.test_context import get_test_context
from core.turnstile import verify_turnstile
from tasks.marketing_notifications import (
    send_application_confirmation,
    send_contact_confirmation,
    send_newsletter_confirmation,
    send_waitlist_confirmation,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# WAITLIST
# ══════════════════════════════════════════════════════════════════════════════


def _waitlist_signup_impl(data: WaitlistSignupRequest, db: Session):
    """
    Core waitlist signup logic — shared between public and /test endpoints.
    Returns (WaitlistSignupResponse, http_status_int).
    """
    new_signup = MarketingWaitlistSignup(
        email=data.email.lower(),
        name=data.name,
        trade=data.trade,
        company_size=data.company_size,
        state=data.state,  # NEW — MKT-B9
        notes=data.notes,  # NEW — MKT-B9
        source=data.source,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
    )

    try:
        with db.begin_nested():
            db.add(new_signup)
            db.flush()
    except IntegrityError:
        existing = (
            db.exec(
                select(MarketingWaitlistSignup).where(
                    MarketingWaitlistSignup.email == data.email.lower()
                )
            ).first()
            or db.exec(
                select(MarketingWaitlistSignup).where(
                    MarketingWaitlistSignup.email == data.email
                )
            ).first()
        )

        if existing is None:
            raise HTTPException(
                status_code=500, detail="Unexpected error processing signup"
            )

        position = _waitlist_position(db, existing.id)
        _dispatch(
            send_waitlist_confirmation,
            email=str(existing.email),
            trade=existing.trade,
            company_size=existing.company_size,
            source=existing.source,
            position=position,
        )
        return (
            WaitlistSignupResponse(
                status="success", message="You're on the list!", position=position
            ),
            200,
        )

    db.commit()
    db.refresh(new_signup)
    position = _waitlist_position(db, new_signup.id)
    _dispatch(
        send_waitlist_confirmation,
        email=data.email,
        trade=data.trade,
        company_size=data.company_size,
        source=data.source,
        position=position,
    )
    return (
        WaitlistSignupResponse(
            status="success", message="You're on the list!", position=position
        ),
        201,
    )


def _waitlist_position(db: Session, signup_id) -> int:
    target = db.exec(
        select(MarketingWaitlistSignup).where(MarketingWaitlistSignup.id == signup_id)
    ).first()
    if target is None:
        return 1
    count = db.exec(
        select(func.count(MarketingWaitlistSignup.id)).where(
            MarketingWaitlistSignup.is_active == True,
            MarketingWaitlistSignup.created_at <= target.created_at,
        )
    ).one()
    return max(1, int(count))


@router.post("/waitlist/test", status_code=201, summary="[TEST] Waitlist signup")
def waitlist_signup_test(data: WaitlistSignupRequest, db: Session = Depends(get_db)):
    """Dev/QA only. Skips Turnstile + honeypot. Blocked in staging/production."""
    get_test_context()
    body, http_status = _waitlist_signup_impl(data, db)
    if http_status == 200:
        return JSONResponse(status_code=200, content=body.model_dump())
    return body


@router.post("/waitlist", status_code=201, summary="Join the Pilot for Trades waitlist")
@limiter.limit("10/hour")
async def waitlist_signup(
    request: Request, body: WaitlistSignupRequest, db: Session = Depends(get_db)
):
    """Public waitlist signup — Turnstile + honeypot + rate limit."""
    if body.honeypot:
        raise HTTPException(status_code=400, detail="Invalid request")
    if not await verify_turnstile(body.cf_turnstile_response):
        raise HTTPException(status_code=400, detail="Invalid request")
    response_body, http_status = _waitlist_signup_impl(body, db)
    if http_status == 200:
        return JSONResponse(status_code=200, content=response_body.model_dump())
    return response_body


# ══════════════════════════════════════════════════════════════════════════════
# CONTACT FORM
# ══════════════════════════════════════════════════════════════════════════════


def _contact_submission_impl(
    data: ContactSubmissionRequest, db: Session
) -> ContactSubmissionResponse:
    """
    Insert a contact submission row and fire email notifications.
    Contact form never deduplicates — every submission is stored.
    """
    submission = MarketingContactSubmission(
        name=data.name,
        email=data.email.lower(),
        company=data.company,
        trade=data.trade,
        subject=data.subject,
        message=data.message,
        source_page=data.source_page,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    _dispatch(
        send_contact_confirmation,
        name=data.name,
        email=data.email,
        subject=data.subject,
        message=data.message,
        source_page=data.source_page,
        company=data.company,
        trade=data.trade,
    )

    return ContactSubmissionResponse(
        status="success",
        message="Your message has been sent. We'll respond within 24 hours.",
    )


@router.post("/contact/test", status_code=201, summary="[TEST] Contact form submit")
def contact_submit_test(data: ContactSubmissionRequest, db: Session = Depends(get_db)):
    """Dev/QA only. Skips Turnstile + honeypot. Blocked in staging/production."""
    get_test_context()
    return _contact_submission_impl(data, db)


@router.post(
    "/contact", status_code=201, summary="Submit the Pilot for Trades contact form"
)
@limiter.limit("10/hour")
async def contact_submit(
    request: Request, body: ContactSubmissionRequest, db: Session = Depends(get_db)
):
    """Public contact form — Turnstile + honeypot + rate limit."""
    if body.honeypot:
        raise HTTPException(status_code=400, detail="Invalid request")
    if not await verify_turnstile(body.cf_turnstile_response):
        raise HTTPException(status_code=400, detail="Invalid request")
    return _contact_submission_impl(body, db)


# ══════════════════════════════════════════════════════════════════════════════
# NEWSLETTER
# ══════════════════════════════════════════════════════════════════════════════


def _newsletter_subscribe_impl(data: NewsletterSubscribeRequest, db: Session):
    """
    Insert newsletter subscriber or return 200 on duplicate (no enumeration).
    Returns (NewsletterSubscribeResponse, http_status_int).
    """
    new_sub = MarketingNewsletterSubscriber(
        email=data.email.lower(),
        trade_interest=data.trade_interest,
        content_preferences=data.content_preferences,
        source=data.source,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
    )

    try:
        with db.begin_nested():
            db.add(new_sub)
            db.flush()
    except IntegrityError:
        # Duplicate email — idempotent 200, no enumeration
        return (
            NewsletterSubscribeResponse(
                status="success",
                message="You're subscribed to Pilot for Trades updates!",
            ),
            200,
        )

    db.commit()
    db.refresh(new_sub)

    _dispatch(
        send_newsletter_confirmation,
        email=data.email,
        trade_interest=data.trade_interest,
        source=data.source,
    )

    return (
        NewsletterSubscribeResponse(
            status="success",
            message="You're subscribed to Pilot for Trades updates!",
        ),
        201,
    )


@router.post("/newsletter/test", status_code=201, summary="[TEST] Newsletter subscribe")
def newsletter_subscribe_test(
    data: NewsletterSubscribeRequest, db: Session = Depends(get_db)
):
    """Dev/QA only. Skips Turnstile + honeypot. Blocked in staging/production."""
    get_test_context()
    body, http_status = _newsletter_subscribe_impl(data, db)
    if http_status == 200:
        return JSONResponse(status_code=200, content=body.model_dump())
    return body


@router.post(
    "/newsletter/unsubscribe",
    status_code=200,
    summary="One-click newsletter unsubscribe",
    response_model=NewsletterUnsubscribeResponse,
)
def newsletter_unsubscribe(token: str, db: Session = Depends(get_db)):
    """
    Verify a signed unsubscribe token and deactivate the subscriber.
    Always returns 200 (idempotent) — unknown emails and already-unsubscribed
    addresses return success to prevent subscriber enumeration.
    """
    # Verify HMAC token
    try:
        email = _verify_newsletter_unsubscribe_token(token)
    except _TokenError:
        raise HTTPException(
            status_code=400, detail="Invalid or expired unsubscribe link"
        )

    # Look up subscriber
    subscriber = db.exec(
        select(MarketingNewsletterSubscriber).where(
            MarketingNewsletterSubscriber.email == email.lower()
        )
    ).first()

    if subscriber is None or not subscriber.is_active:
        # Already unsubscribed or unknown — idempotent 200
        return NewsletterUnsubscribeResponse(
            status="success", message="You've been unsubscribed."
        )

    subscriber.unsubscribed_at = datetime.now(UTC)
    subscriber.is_active = False
    db.add(subscriber)
    db.commit()

    return NewsletterUnsubscribeResponse(
        status="success", message="You've been unsubscribed."
    )


@router.post(
    "/newsletter", status_code=201, summary="Subscribe to Pilot for Trades newsletter"
)
@limiter.limit("10/hour")
async def newsletter_subscribe(
    request: Request, body: NewsletterSubscribeRequest, db: Session = Depends(get_db)
):
    """Public newsletter subscribe — Turnstile + honeypot + rate limit."""
    if body.honeypot:
        raise HTTPException(status_code=400, detail="Invalid request")
    if not await verify_turnstile(body.cf_turnstile_response):
        raise HTTPException(status_code=400, detail="Invalid request")
    response_body, http_status = _newsletter_subscribe_impl(body, db)
    if http_status == 200:
        return JSONResponse(status_code=200, content=response_body.model_dump())
    return response_body


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


class _TokenError(Exception):
    pass


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _verify_newsletter_unsubscribe_token(token: str) -> str:
    """
    Verify an HMAC-signed newsletter unsubscribe token.

    Returns:
        The email address from the verified token.

    Raises:
        _TokenError: If token is invalid, malformed, or expired.
    """
    secret = settings.NEWSLETTER_UNSUBSCRIBE_SECRET
    parts = token.split(".")
    if len(parts) != 2:
        raise _TokenError("Malformed token")

    payload_b64, sig_b64 = parts
    try:
        payload_bytes = _b64url_decode(payload_b64)
    except Exception:
        raise _TokenError("Invalid base64url payload")

    # Verify HMAC
    expected_sig = hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).digest()
    try:
        provided_sig = _b64url_decode(sig_b64)
    except Exception:
        raise _TokenError("Invalid base64url signature")

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise _TokenError("Signature mismatch")

    # Parse payload
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise _TokenError("Payload not valid JSON")

    # Check expiration
    expiration_str = payload.get("expiration")
    if not expiration_str:
        raise _TokenError("Missing expiration field")
    try:
        expiration_dt = datetime.fromisoformat(expiration_str)
    except ValueError:
        raise _TokenError("Invalid expiration format")

    if datetime.now(UTC) > expiration_dt:
        raise _TokenError(f"Token expired at {expiration_str}")

    email = payload.get("email")
    if not email:
        raise _TokenError("Missing email field")

    return email


def _dispatch(task, **kwargs) -> None:
    """Fire-and-forget Celery task. Broker errors are logged but don't fail the response."""
    try:
        task.delay(**kwargs)
    except Exception as exc:
        logger.error("Failed to dispatch %s: %s", task.name, exc, exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# JOB APPLICATION
# ══════════════════════════════════════════════════════════════════════════════


def _application_submit_impl(
    data: JobApplicationRequest, db: Session
) -> JobApplicationResponse:
    """
    Insert a job application row and fire email notifications.
    Applications are never deduplicated — every submission is stored.
    """
    application = MarketingJobApplication(
        name=data.name,
        email=data.email.lower(),
        role=data.role,
        linkedin_url=data.linkedin_url,
        portfolio_url=data.portfolio_url,
        why_interested=data.why_interested,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    _dispatch(
        send_application_confirmation,
        name=data.name,
        email=data.email,
        role=data.role,
        linkedin_url=data.linkedin_url,
        portfolio_url=data.portfolio_url,
        why_interested=data.why_interested,
    )

    return JobApplicationResponse(
        status="success",
        message="Your application has been received. We'll be in touch if it's a fit.",
    )


@router.post(
    "/application/test", status_code=201, summary="[TEST] Job application submit"
)
def application_submit_test(data: JobApplicationRequest, db: Session = Depends(get_db)):
    """Dev/QA only. Skips Turnstile + honeypot. Blocked in staging/production."""
    get_test_context()
    return _application_submit_impl(data, db)


@router.post(
    "/application",
    status_code=201,
    response_model=JobApplicationResponse,
    summary="Submit a job application",
)
@limiter.limit("5/hour")
async def application_submit(
    request: Request, body: JobApplicationRequest, db: Session = Depends(get_db)
):
    """Public job application form — Turnstile + honeypot + rate limit (5/hour, stricter than contact)."""
    if body.honeypot:
        raise HTTPException(status_code=400, detail="Invalid request")
    if not await verify_turnstile(body.cf_turnstile_response):
        raise HTTPException(status_code=400, detail="Invalid request")
    return _application_submit_impl(body, db)
