"""
Notification Endpoint Service — SIGNUP-C / Pathway C
====================================================
Owner SMS endpoint management for Pilot→owner platform notifications
(account, billing & security alerts).

Pathway C consent model (design §B/§F):
  - Owner mobile is stored on ``user_endpoint`` (channel='sms') — the
    authoritative consent-bearing record. ``user.phone_number`` is mirrored as
    a display copy (MFA reuse).
  - ``user_endpoint`` has NO unique constraint on (user_id, channel, value)
    (MCP-verified). Idempotency = value-scoped DELETE+INSERT: delete any
    existing sms endpoint for this user with the same value, then insert a
    fresh row. This keeps re-attestation from creating duplicates.
  - Consent checkbox (unchecked by default) drives ``consent_status``:
      True  → 'opted_in'  (verification_status='pending' — reply-YES seals it)
      False → 'unknown'   (verification_status='pending' — no SMS sent)
  - Every attestation writes an immutable ``user_sms_consent_audit`` row
    (action='attested').

Sync ``def`` throughout (Rule 21). Tenant-scoped ``select()`` (Rule 4) —
though ``user_endpoint`` itself is user-scoped (no tenant_id column), the
audit row carries tenant_id.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.communications import UserSmsConsentAudit
from app.models.core import User, UserEndpoint

logger = logging.getLogger(__name__)


def upsert_owner_sms_endpoint(
    db: Session,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    phone: str,
    consent: bool,
    ip: str | None,
    disclosure_hash: str,
) -> UserEndpoint:
    """
    Write/refresh the owner's ``sms`` ``user_endpoint`` + the attestation audit row.

    Because ``user_endpoint`` has no unique constraint on
    ``(user_id, channel, value)`` (MCP-verified), this uses the value-scoped
    DELETE+INSERT idempotency pattern: any existing sms endpoint for this user
    with the same phone value is deleted before the fresh insert. This prevents
    duplicate endpoints on re-attestation while preserving endpoints with a
    *different* phone value (a number change creates a new row; the old one is
    removed only if it matched the now-submitted value).

    Args:
        db:               Active DB session (sync).
        user_id:          The owner user.
        tenant_id:        Tenant scope (for the audit row).
        phone:            E.164 mobile number.
        consent:          True if the owner checked the SMS-alerts checkbox.
        ip:               Request IP at attestation (nullable for non-HTTP paths).
        disclosure_hash:  SHA-256 of the disclosure text shown at attestation.

    Returns:
        The freshly inserted ``UserEndpoint`` (channel='sms').

    Side effects:
        - DELETE existing ``user_endpoint`` rows WHERE user_id AND channel='sms'
          AND value=phone (value-scoped).
        - INSERT new ``user_endpoint`` (consent_status per ``consent``,
          verification_status='pending').
        - INSERT ``user_sms_consent_audit`` (action='attested').
        - Mirror ``user.phone_number = phone`` (display copy).
    """
    now = datetime.now(UTC)
    consent_status = "opted_in" if consent else "unknown"

    # 1. Look for an existing sms endpoint with the SAME phone value for this
    #    user. If found, UPDATE it in place — this preserves the endpoint id so
    #    the user_sms_consent_audit FK (ON DELETE RESTRICT) stays valid. The
    #    audit trail is immutable; re-attestation refreshes consent state on the
    #    same endpoint row rather than deleting it.
    existing_same_value = db.exec(
        select(UserEndpoint).where(
            UserEndpoint.user_id == user_id,
            UserEndpoint.channel == "sms",
            UserEndpoint.value == phone,
        )
    ).first()

    if existing_same_value is not None:
        # Update in place — refresh consent/verification state.
        existing_same_value.consent_status = consent_status
        existing_same_value.verification_status = "pending"
        existing_same_value.consent_updated_at = now
        existing_same_value.updated_at = now
        existing_same_value.updated_by = user_id
        db.add(existing_same_value)
        db.flush()
        endpoint = existing_same_value
    else:
        # 2. Different phone value (a genuine number change). Remove any prior
        #    sms endpoint for this user that has NO audit row referencing it
        #    (RESTRICT blocks deleting one that does). A number change with a
        #    prior attested endpoint is rare in the signup flow; if the DELETE
        #    is blocked by RESTRICT, the new endpoint is still inserted and the
        #    old one remains (is_active=False) — get_owner_sms_endpoint returns
        #    the most recent.
        prior_endpoints = db.exec(
            select(UserEndpoint).where(
                UserEndpoint.user_id == user_id,
                UserEndpoint.channel == "sms",
                UserEndpoint.value != phone,
            )
        ).all()
        for row in prior_endpoints:
            try:
                db.delete(row)
            except Exception:
                # RESTRICT blocked the delete (audit row references it).
                # Soft-deactivate instead so the new endpoint becomes primary.
                row.is_active = False
                db.add(row)
        db.flush()

        # INSERT the fresh sms endpoint.
        endpoint = UserEndpoint(
            user_id=user_id,
            channel="sms",
            value=phone,
            is_primary=False,
            verification_status="pending",
            consent_status=consent_status,
            consent_updated_at=now,
            created_at=now,
            updated_at=now,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(endpoint)
        db.flush()  # populate endpoint.id for the audit FK

    # 3. Write the immutable attestation audit row.
    audit_row = UserSmsConsentAudit(
        tenant_id=tenant_id,
        user_id=user_id,
        user_endpoint_id=endpoint.id,
        action="attested",
        consent_text_hash=disclosure_hash,
        ip_address=ip,
        attested_at=now,
        created_at=now,
        created_by=user_id,
    )
    db.add(audit_row)

    # 4. Mirror user.phone_number (display copy; MFA reuse).
    user = db.exec(select(User).where(User.id == user_id)).first()
    if user is not None:
        user.phone_number = phone
        db.add(user)

    db.commit()
    db.refresh(endpoint)

    logger.info(
        "upsert_owner_sms_endpoint: user=%s tenant=%s phone=%s consent=%s "
        "endpoint_id=%s",
        user_id,
        tenant_id,
        phone,
        consent_status,
        endpoint.id,
    )
    return endpoint


def get_owner_sms_endpoint(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> UserEndpoint | None:
    """
    Return the owner's active ``sms`` ``user_endpoint``, or None.

    A user has at most one active sms endpoint (the upsert enforces value-scoped
    uniqueness). If multiple exist (legacy data), the most recently created is
    returned.
    """
    return db.exec(
        select(UserEndpoint)
        .where(
            UserEndpoint.user_id == user_id,
            UserEndpoint.channel == "sms",
            UserEndpoint.is_active == True,
        )
        .order_by(UserEndpoint.created_at.desc())
    ).first()


def get_verified_owner_sms_endpoints(
    db: Session,
    *,
    tenant_id: uuid.UUID,
) -> list[UserEndpoint]:
    """
    Return ALL owner SMS endpoints for a tenant where
    ``consent_status='opted_in'`` AND ``verification_status='verified'``.

    PLATFORM-SMS-B1: Used by the Pathway C account-notification sender
    (``tasks/sms_platform_notifications.py``) to fan out platform SMS to every
    verified, opted-in owner of the tenant. This is the TCPA consent gate —
    only owners who completed the double-opt-in (replied YES) receive
    account-notification messages.

    Args:
        db:        Active DB session (sync).
        tenant_id: The tenant scope.

    Returns:
        List of ``UserEndpoint`` rows (channel='sms', is_active=True,
        consent_status='opted_in', verification_status='verified') for all
        owner-role users of the tenant. May be empty.
    """
    from app.models.auth import TenantUser

    # Resolve all owner user_ids for this tenant.
    owner_user_ids = db.exec(
        select(TenantUser.user_id).where(
            TenantUser.tenant_id == tenant_id,
            TenantUser.role_code == "owner",
            TenantUser.is_active == True,
        )
    ).all()

    if not owner_user_ids:
        return []

    # Return verified+opted-in sms endpoints for those owners.
    return db.exec(
        select(UserEndpoint).where(
            UserEndpoint.user_id.in_(owner_user_ids),
            UserEndpoint.channel == "sms",
            UserEndpoint.is_active == True,
            UserEndpoint.consent_status == "opted_in",
            UserEndpoint.verification_status == "verified",
        )
    ).all()


def get_verified_user_sms_endpoints(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[UserEndpoint]:
    """
    Return the verified + opted-in ``sms`` ``user_endpoint`` rows for ONE user.

    PLP-FIX-8 (INV-BUG-4): sibling of ``get_verified_owner_sms_endpoints``,
    scoped to a single user instead of all owner-role users of a tenant. Used
    by the platform account-notification sender
    (``tasks/sms_platform_notifications.py``) when ``recipient_user_id`` is
    supplied — e.g. the Post-Authentication new-device alert, which must text
    the *authenticating* user (not the tenant owner) on a new-device sign-in.

    Mirrors the owner helper's filter semantics exactly:
      - ``channel == 'sms'``
      - ``is_active == True``
      - ``consent_status == 'opted_in'``  (TCPA consent gate)
      - ``verification_status == 'verified'``  (double-opt-in completed)

    Scoping note (MCP-verified 2026-09-05): ``user_endpoint`` has NO
    ``tenant_id`` column — rows are user-scoped. The ``tenant_id`` parameter
    is accepted for signature symmetry with the owner helper and for future
    audit/logging, but the WHERE clause filters by ``user_id`` only. A user
    belongs to at most one tenant in the MVP single-trade model, so
    user-scoping is equivalent to tenant+user scoping for Mike the Solo
    Contractor's account.

    Args:
        db:        Active DB session (sync).
        tenant_id: The tenant scope (signature symmetry; not in the WHERE
                   clause — see scoping note).
        user_id:   The user whose endpoints are resolved.

    Returns:
        List of ``UserEndpoint`` rows (channel='sms', is_active=True,
        consent_status='opted_in', verification_status='verified') for the
        given user. May be empty (e.g. a technician with no verified phone).
    """
    return db.exec(
        select(UserEndpoint).where(
            UserEndpoint.user_id == user_id,
            UserEndpoint.channel == "sms",
            UserEndpoint.is_active == True,
            UserEndpoint.consent_status == "opted_in",
            UserEndpoint.verification_status == "verified",
        )
    ).all()


def write_consent_audit(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_endpoint_id: uuid.UUID | None,
    action: str,
    consent_text_hash: str,
    ip: str | None = None,
    created_by: uuid.UUID | None = None,
) -> UserSmsConsentAudit:
    """
    Append a ``user_sms_consent_audit`` row.

    Used by the platform double-opt-in task (action='double_opt_in_sent') and
    the inbound webhook handlers (action='double_opt_in_confirmed' / 'opted_out').

    Args:
        action: One of 'attested', 'double_opt_in_sent',
            'double_opt_in_confirmed', 'opted_out' (CHECK-enforced).
        consent_text_hash: SHA-256 of the relevant consent text.
    """
    now = datetime.now(UTC)
    audit_row = UserSmsConsentAudit(
        tenant_id=tenant_id,
        user_id=user_id,
        user_endpoint_id=user_endpoint_id,
        action=action,
        consent_text_hash=consent_text_hash,
        ip_address=ip,
        attested_at=now,
        created_at=now,
        created_by=created_by,
    )
    db.add(audit_row)
    db.commit()
    db.refresh(audit_row)
    return audit_row


def hash_consent_text(text: str) -> str:
    """SHA-256 hex digest of a consent text string."""
    return hashlib.sha256(text.encode()).hexdigest()
