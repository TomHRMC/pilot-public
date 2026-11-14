#!/usr/bin/env python3
"""Maintenance Broadcast SMS CLI — PLATFORM-SMS-B2 / Pathway C (Sample 4).

Operator-run script that enqueues the existing B1 task
(``send_platform_account_notification_sms``) once per eligible tenant for the
``platform_maintenance_broadcast`` notification type (campaign CXXXXXX
Sample 4). The stored body contains ``{{ maint_date }}`` / ``{{ maint_window }}``
Jinja2 placeholders; this script supplies the values via ``template_context``.

Usage:
    # DRY RUN (default) — logs eligible-tenant count + per-tenant endpoint
    # counts. Enqueues NOTHING.
    python -m scripts.broadcast_maintenance_sms \\
        --date "Sun 08-02-2026" --window "2:00–3:00 AM ET"

    # LIVE — enqueues one task per eligible tenant.
    python -m scripts.broadcast_maintenance_sms \\
        --date "Sun 08-02-2026" --window "2:00–3:00 AM ET" --i-am-sure

Eligibility (single source of truth — same function the task uses):
    1. ``SELECT DISTINCT tenant_id FROM tenant_user WHERE is_active = true``
    2. For each, ``get_verified_owner_sms_endpoints(db, tenant_id=tid)`` ≥ 1.
    3. No billing/subscription filtering (design §G-10).

Value validation (design §G-5): ``--date`` and ``--window`` must match
``^[A-Za-z0-9: \\-–]+$`` (alphanumerics, colon, space, hyphen, en-dash U+2013).
This keeps the Jinja2 ``autoescape=True`` render byte-identical and blocks
``{``/``}`` template injection. On rejection: exit code 2.

This file contains no campaign-locked SMS body literal (guardrail grep target).
The campaign-locked body lives only in the DB (loaded by the task).

Sync ``def`` throughout (Rule 21). Importing
``tasks.sms_platform_notifications`` pulls ``core.celery_app`` — expected and
fine in the backend environment.

Design: dev-docs/architecture-design/batch-designs/batch-platform-sms-b2-design.md §F.2
ADR-0013 (Pathway C).
"""

from __future__ import annotations

import argparse
import logging
import re
import sys

from sqlmodel import Session, select

from app.models.auth import TenantUser
from core.db import engine
from services.notification_endpoints import get_verified_owner_sms_endpoints
from tasks.sms_platform_notifications import send_platform_account_notification_sms

logger = logging.getLogger(__name__)

# Allowlist for --date / --window values (design §G-5).
# Alphanumerics, colon, space, hyphen, en-dash U+2013. Excludes &, <, >, quotes,
# braces — keeps the Jinja2 autoescape=True render byte-identical and blocks
# template injection.
ALLOWLIST = re.compile(r"^[A-Za-z0-9: \-–]+$")

# The notification type code for Sample 4 (campaign CXXXXXX).
_TYPE_CODE = "platform_maintenance_broadcast"


def _validate_value(name: str, value: str) -> str:
    """Validate a CLI value against the allowlist. Exit 2 on rejection."""
    if not value or not ALLOWLIST.match(value):
        logger.error(
            "Invalid value for --%s: %r. Must match %s (alphanumerics, colon, "
            "space, hyphen, en-dash only — no &, <, >, quotes, or braces).",
            name,
            value,
            ALLOWLIST.pattern,
        )
        sys.exit(2)
    return value


def _resolve_eligible_tenants(db: Session) -> list[tuple[str, int]]:
    """
    Return a list of (tenant_id_str, endpoint_count) for eligible tenants.

    Eligible = has ≥ 1 verified+opted-in owner sms endpoint. No billing filter.
    """
    distinct_tenant_ids = db.exec(
        select(TenantUser.tenant_id).where(TenantUser.is_active == True).distinct()
    ).all()

    eligible: list[tuple[str, int]] = []
    for tid in distinct_tenant_ids:
        endpoints = get_verified_owner_sms_endpoints(db, tenant_id=tid)
        count = len(endpoints)
        if count >= 1:
            eligible.append((str(tid), count))
    return eligible


def main(date: str, window: str, i_am_sure: bool) -> int:
    """Entry point. Returns exit code (0 on success, 2 on validation error)."""
    date = _validate_value("date", date)
    window = _validate_value("window", window)

    logger.info(
        "broadcast_maintenance_sms: date=%r window=%r i_am_sure=%s",
        date,
        window,
        i_am_sure,
    )

    with Session(engine) as db:
        eligible = _resolve_eligible_tenants(db)

    total_endpoints = sum(count for _, count in eligible)
    logger.info(
        "broadcast_maintenance_sms: tenants_eligible=%d endpoints=%d",
        len(eligible),
        total_endpoints,
    )

    if not i_am_sure:
        for tid, count in eligible:
            logger.info(
                "  DRY RUN — tenant=%s owner_endpoints=%d (not enqueued)",
                tid,
                count,
            )
        logger.info(
            "DRY RUN — tenants_eligible=%d endpoints=%d "
            "(re-run with --i-am-sure to enqueue)",
            len(eligible),
            total_endpoints,
        )
        return 0

    tasks_enqueued = 0
    for tid, count in eligible:
        send_platform_account_notification_sms.delay(
            tenant_id=tid,
            type_code=_TYPE_CODE,
            template_context={"maint_date": date, "maint_window": window},
        )
        tasks_enqueued += 1
        logger.info(
            "  enqueued: tenant=%s owner_endpoints=%d type_code=%s",
            tid,
            count,
            _TYPE_CODE,
        )

    logger.info(
        "tenants_eligible=%d tasks_enqueued=%d",
        len(eligible),
        tasks_enqueued,
    )
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Maintenance Broadcast SMS CLI (PLATFORM-SMS-B2 / Sample 4). "
            "Enqueues platform_maintenance_broadcast SMS to eligible tenants."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date",
        required=True,
        help='Maintenance date string, e.g. "Sun 08-02-2026".',
    )
    parser.add_argument(
        "--window",
        required=True,
        help='Maintenance window string, e.g. "2:00–3:00 AM ET" (en-dash U+2013).',
    )
    parser.add_argument(
        "--i-am-sure",
        action="store_true",
        help="Enqueue tasks. Without this flag, runs as a dry run (no enqueue).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _parse_args()
    sys.exit(main(args.date, args.window, args.i_am_sure))
