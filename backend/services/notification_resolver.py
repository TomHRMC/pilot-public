"""
Notification preference resolver for Pilot for Trades.

Three-tier resolution chain per arch doc §3.5.4:
  User-level preference → Tenant-level preference → Notification default policy
  (tenant override) → Notification default policy (system default) → False

Established in B10/A58. Consumed by:
  - tasks/notification_worker.py::_send_notification_impl() (dispatcher gate)
  - api/routes/notification_preferences.py::_build_full_matrix() (GET preferences)
"""

import logging
from uuid import UUID

from sqlmodel import Session, select

from app.models.system import (
    NotificationCategorySubTrigger,
    NotificationDefaultPolicy,
    NotificationPreference,
)

logger = logging.getLogger(__name__)


def get_effective_preference(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: str,
    channel: str,
    pref_cache: dict | None = None,
) -> bool:
    """
    Resolve the effective notification preference for a user × category × channel combination.

    Resolution order (§3.5.4):
      1. User-level row in notification_preference (user_id = user_id)
      2. Tenant-level row in notification_preference (user_id IS NULL)
      3. Tenant-override row in notification_default_policy (tenant_id = tenant_id)
      4. System-default row in notification_default_policy (tenant_id IS NULL)
      5. Fallback: False

    Args:
        db:           Active SQLModel session.
        tenant_id:    Tenant scope for the preference lookup.
        user_id:      Recipient user being evaluated.
        category_id:  Notification category (e.g., 'job_activity').
        channel:      Delivery channel ('push' | 'email' | 'in_app').
        pref_cache:   Optional in-memory dict for single-poll-cycle caching.
                      Key: (user_id, category_id, channel). Callers manage lifecycle.

    Returns:
        bool — True if the notification should be delivered via this channel to this user.
    """
    cache_key = (user_id, category_id, channel)

    if pref_cache is not None and cache_key in pref_cache:
        return pref_cache[cache_key]

    result = _resolve_preference(db, tenant_id, user_id, category_id, channel)

    if pref_cache is not None:
        pref_cache[cache_key] = result

    return result


def _resolve_preference(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: str,
    channel: str,
) -> bool:
    """Inner resolver — no caching."""

    # Tier 1: User-level override
    user_pref = db.exec(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
            NotificationPreference.category_id == category_id,
            NotificationPreference.channel == channel,
        )
    ).first()
    if user_pref is not None:
        return user_pref.enabled

    # Tier 2: Tenant-level override in notification_preference (user_id IS NULL)
    tenant_pref = db.exec(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == None,
            NotificationPreference.category_id == category_id,
            NotificationPreference.channel == channel,
        )
    ).first()
    if tenant_pref is not None:
        return tenant_pref.enabled

    # Tier 3: Tenant override row in notification_default_policy
    tenant_default = db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id,
            NotificationDefaultPolicy.category_id == category_id,
            NotificationDefaultPolicy.channel == channel,
        )
    ).first()
    if tenant_default is not None:
        return tenant_default.enabled

    # Tier 4: System-default row in notification_default_policy (tenant_id IS NULL)
    system_default = db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == None,
            NotificationDefaultPolicy.category_id == category_id,
            NotificationDefaultPolicy.channel == channel,
        )
    ).first()
    if system_default is not None:
        return system_default.enabled

    # Tier 5: Fallback constant
    return False


def apply_forced_minimum_override(
    base_enabled: bool,
    channel: str,
    sub_trigger_id: str | None,
    recipient_user_id: UUID,
    recipient_user_id_originating: UUID | None,
    db: Session,
) -> bool:
    """
    Apply forced-minimum push override after the three-tier resolution chain.

    Forced-minimum only applies to the 'push' channel. Email and in-app always
    respect the resolved preference — no forced-minimum for those channels.

    Forced-minimum semantics (per arch §3.5.3):
      - forced_minimum_push_uniform: override to True for ALL recipients
      - forced_minimum_push_recipient_only: override to True ONLY when
        recipient_user_id == recipient_user_id_originating

    Args:
        base_enabled:                  Result from get_effective_preference().
        channel:                       Delivery channel being evaluated.
        sub_trigger_id:                Sub-trigger ID from the outbox row (may be None).
        recipient_user_id:             User being evaluated for delivery.
        recipient_user_id_originating: The 'owning' user from the outbox row.
        db:                            Active SQLModel session (needed to fetch sub_trigger row).

    Returns:
        bool — Final delivery decision after forced-minimum override applied.
    """
    # Forced-minimum only applies to push channel
    if channel != "push" or sub_trigger_id is None:
        return base_enabled

    sub_trigger = db.exec(
        # FIND-169: sub_trigger_id → code on NotificationCategorySubTrigger
        select(NotificationCategorySubTrigger).where(
            NotificationCategorySubTrigger.code == sub_trigger_id
        )
    ).first()

    if sub_trigger is None:
        return base_enabled

    # Uniform forced-minimum: override for ALL recipients regardless of preference
    if sub_trigger.forced_minimum_push_uniform:
        return True

    # Recipient-only forced-minimum: override ONLY for the originating recipient
    if (
        sub_trigger.forced_minimum_push_recipient_only
        and recipient_user_id_originating is not None
        and recipient_user_id == recipient_user_id_originating
    ):
        return True

    return base_enabled


def should_deliver(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: str,
    channel: str,
    sub_trigger_id: str | None,
    recipient_user_id_originating: UUID | None,
    pref_cache: dict | None = None,
) -> bool:
    """
    Combined resolver: get_effective_preference() + apply_forced_minimum_override().

    Single-call interface for the dispatcher gate. Returns the final delivery
    decision for one (user × category × channel) combination.

    Args:
        db:                             Active SQLModel session.
        tenant_id:                      Tenant scope.
        user_id:                        Recipient user being evaluated.
        category_id:                    Notification category.
        channel:                        Delivery channel.
        sub_trigger_id:                 Sub-trigger ID from outbox row (may be None).
        recipient_user_id_originating:  The 'owning' user from the outbox row (may be None).
        pref_cache:                     Optional in-memory cache dict.

    Returns:
        bool — True = deliver; False = suppress.
    """
    base = get_effective_preference(
        db, tenant_id, user_id, category_id, channel, pref_cache
    )
    return apply_forced_minimum_override(
        base, channel, sub_trigger_id, user_id, recipient_user_id_originating, db
    )
