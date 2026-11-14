"""
test_fire_templates.py — Manual QA tool for firing notification and email templates.

NOT part of the seed system. NOT run by tests or automation. NOT registered in reset_dev_db.py.
Fires one template via SendGrid (email channel only, this version) for QA verification.

Usage:
  # Dry-run an email_template (renders + prints, no send):
  python migrations/scripts/test_fire_templates.py \\
      --email-template invoice_sent \\
      --recipient tom@pilotfortrades.com \\
      --dry-run

  # Send an email_template via SendGrid:
  python migrations/scripts/test_fire_templates.py \\
      --email-template invoice_sent \\
      --recipient tom@pilotfortrades.com

  # Send a notification_template by type code:
  python migrations/scripts/test_fire_templates.py \\
      --template-type quote_accepted \\
      --channel email \\
      --recipient tom@pilotfortrades.com

  # Dry-run a notification_template with a specific locale:
  python migrations/scripts/test_fire_templates.py \\
      --template-type dunning_reminder \\
      --channel email \\
      --recipient tom@pilotfortrades.com \\
      --locale en \\
      --dry-run

  # Refresh the cached template catalog from the live DB:
  python migrations/scripts/test_fire_templates.py --db-update

  # Optional: specify tenant and locale
  python migrations/scripts/test_fire_templates.py \\
      --email-template invoice_sent \\
      --recipient tom@pilotfortrades.com \\
      --tenant-id 00000000-0000-0000-0000-000000000001 \\
      --locale en
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add backend/ to sys.path so core.* and services.* imports resolve correctly
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text  # noqa: E402

from core.config import settings  # noqa: E402
from migrations.scripts._db_utils import get_db_session  # noqa: E402

# ── Template catalog JSON cache ────────────────────────────────────────────────
CATALOG_PATH = Path(__file__).parent / "data" / "template_catalog.json"


def _load_catalog() -> dict:
    """Load the template catalog from the JSON cache file.

    Returns an empty catalog dict if the file doesn't exist yet.
    """
    if not CATALOG_PATH.exists():
        return {
            "_meta": {"last_updated": "never — run --db-update"},
            "email_templates": [],
            "notification_templates": [],
            "communication_templates": [],
        }
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _get_active_channels(catalog: dict) -> list[str]:
    """Return the list of channels currently implemented in this script (from catalog._meta)."""
    return catalog.get("_meta", {}).get("active_channels", ["email"])


def _build_help_epilog(catalog: dict) -> str:
    """Build the --help epilog string from the cached catalog."""
    meta = catalog.get("_meta", {})
    last_updated = meta.get("last_updated", "unknown")
    active_channels = meta.get("active_channels", ["email"])
    all_channels = meta.get("all_channels", ["email", "in_app", "push", "sms"])

    email_templates = catalog.get("email_templates", [])
    notification_templates = catalog.get("notification_templates", [])
    communication_templates = catalog.get("communication_templates", [])

    active_str = ", ".join(active_channels)
    all_str = ", ".join(all_channels)
    pending = [c for c in all_channels if c not in active_channels]
    pending_str = ", ".join(pending) if pending else "none"

    lines = [
        "",
        "examples:",
        "  # Dry-run an email_template (renders + prints, no send):",
        "  python migrations/scripts/test_fire_templates.py \\",
        "      --email-template invoice_sent \\",
        "      --recipient tom@pilotfortrades.com \\",
        "      --dry-run",
        "",
        "  # Send an email_template via SendGrid:",
        "  python migrations/scripts/test_fire_templates.py \\",
        "      --email-template invoice_sent \\",
        "      --recipient tom@pilotfortrades.com",
        "",
        "  # Send a notification_template by type code:",
        "  python migrations/scripts/test_fire_templates.py \\",
        "      --template-type quote_accepted \\",
        "      --channel email \\",
        "      --recipient tom@pilotfortrades.com",
        "",
        "  # Refresh cached template catalog from live DB:",
        "  python migrations/scripts/test_fire_templates.py --db-update",
        "",
        f"channel support (last updated: {last_updated}):",
        f"  active (implemented) : {active_str}",
        f"  all DB channels      : {all_str}",
        f"  pending impl         : {pending_str}",
        "",
        f"template catalog (last updated: {last_updated}):",
        "",
    ]

    # email_templates
    lines.append("  email_template IDs (use with --email-template):")
    if email_templates:
        for t in email_templates:
            active_flag = "✅" if t.get("is_active", True) else "❌"
            cat = t.get("category", "")
            tid = t["template_id"]
            name = t.get("display_name", "")
            lines.append(f"    {active_flag} {tid:<42} {name}  [{cat}]")
    else:
        lines.append("    (none — run --db-update to populate)")
    lines.append("")

    # notification_templates
    lines.append("  notification_template type codes (use with --template-type):")
    if notification_templates:
        for t in notification_templates:
            channels = ", ".join(t.get("channels", []))
            lines.append(f"    • {t['type_code']:<42} channels: {channels}")
    else:
        lines.append("    (none — run --db-update to populate)")
    lines.append("")

    # communication_templates
    lines.append(
        "  communication_template codes (customer-facing SMS/email, for reference):"
    )
    if communication_templates:
        for t in communication_templates:
            active_flag = "✅" if t.get("is_active", True) else "❌"
            channels = ", ".join(t.get("channels", []))
            lines.append(
                f"    {active_flag} {t['template_code']:<42} channels: {channels}"
            )
    else:
        lines.append("    (none — run --db-update to populate)")
    lines.append("")

    lines += [
        "notes:",
        "  - Uses hardcoded TEST_RENDER_CONTEXT for variable substitution (no real DB entity lookup)",
        "  - Sends from SENDGRID_FROM_EMAIL configured in .env / settings",
        "  - If SENDGRID_API_KEY is not set, send is mocked (returns status=sent, http_status=202)",
        f"  - Default tenant: settings.TEST_TENANT_ID ({settings.TEST_TENANT_ID})",
        "  - See: backend/migrations/scripts/README-test-fire-templates.md for full documentation",
    ]
    return "\n".join(lines)


# ── Test data context — hardcoded placeholders for QA sends ───────────────────
TEST_RENDER_CONTEXT = {
    "customer_name": "Dev Owner (Test Send)",
    "company_name": "Pilot Dev Tenant",
    "tenant_name": "Pilot Dev Tenant",
    "company_domain": "pilotfortrades.com",
    "invoice_total": "955.96",
    "invoice_url": "https://app.pilotfortrades.com/invoices/test-preview",
    "invoice_id": "INV-900004",
    "due_date": "2026-08-22",
    "quote_number": "QUO-900004",
    "quote_url": "https://app.pilotfortrades.com/quotes/test-preview",
    "quote_total": "1200.00",
    "quote_id": "QUO-900004",
    "job_title": "Panel Upgrade — Test Send",
    "scheduled_date": "2026-08-01",
    "scheduled_time": "9:00 AM",
    "tech_name": "Alex (Tech User)",
    "user_name": "Dev Owner (Test Send)",
    "amount": "955.96",
    "payment_date": "2026-07-23",
    "plan_name": "Starter",
    "next_billing_date": "2026-08-23",
    "update_url": "https://app.pilotfortrades.com/billing",
    "upgrade_url": "https://app.pilotfortrades.com/upgrade",
    "days_remaining": "7",
    "verify_url": "https://app.pilotfortrades.com/verify/test-token",
    "reset_url": "https://app.pilotfortrades.com/reset/test-token",
    "expires_in": "24 hours",
    "decline_reason": "pricing",
    "expires_at": "2026-08-22",
}

# ─────────────────────────────────────────────────────────────────────────────


def _substitute(template_str: str, context: dict) -> str:
    """
    Substitute {{variable}} placeholders using Python str.format_map().
    Unresolved variables are left as-is (no KeyError raised).
    Matches the logic in services/email_template_renderer.py.
    """
    normalized = template_str.replace("{{", "{").replace("}}", "}")

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return f"{{{key}}}"

    return normalized.format_map(_SafeDict(context))


def parse_args(catalog: dict):
    """Build and return the argument parser, loading epilog from the catalog cache."""
    parser = argparse.ArgumentParser(
        description=(
            "test_fire_templates.py — QA tool for manual template test-fire.\n\n"
            "Fires one email template or notification template via SendGrid for QA verification.\n"
            "Email channel only (this version). NOT part of the seed system.\n"
            "NOT run by any automated test or CI pipeline.\n\n"
            "Run from backend/ directory: cd backend && source .venv/bin/activate"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_build_help_epilog(catalog),
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--email-template",
        metavar="TEMPLATE_ID",
        help="template_id from email_template table (e.g. invoice_sent)",
    )
    mode_group.add_argument(
        "--template-type",
        metavar="TYPE_CODE",
        help="notification_type_code from notification_template table (e.g. quote_accepted)",
    )
    mode_group.add_argument(
        "--db-update",
        action="store_true",
        help=(
            "Refresh the template catalog cache from the live DB and exit. "
            "Updates data/template_catalog.json with current email_template, "
            "notification_template, and communication_template rows. "
            "Does not send any email."
        ),
    )
    parser.add_argument(
        "--channel",
        default="email",
        help="Notification channel. Only 'email' is supported. Default: email",
    )
    parser.add_argument(
        "--recipient",
        default=None,
        metavar="EMAIL",
        help="Email address to send to (required for --email-template and --template-type)",
    )
    parser.add_argument(
        "--tenant-id",
        default=None,
        metavar="UUID",
        help="Tenant UUID. Defaults to settings.TEST_TENANT_ID",
    )
    parser.add_argument(
        "--locale",
        default="en",
        help="Locale for notification_template lookup. Default: en",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and print template without sending",
    )
    return parser


def _get_tenant_id(args) -> str:
    if args.tenant_id:
        return args.tenant_id
    return settings.TEST_TENANT_ID


def mode_db_update() -> int:
    """Query the live DB and refresh data/template_catalog.json.

    Preserves _meta.active_channels (implementation gate — set manually when a
    new channel is implemented in the script). Updates all_channels from the DB.

    Returns exit code: 0 = success, 1 = error.
    """
    print("=== test_fire_templates.py --db-update ===\n")
    print(f"  Querying live DB to refresh: {CATALOG_PATH.relative_to(backend_dir)}\n")

    # Preserve the existing active_channels from the current catalog (don't overwrite)
    existing_catalog = _load_catalog()
    existing_active_channels = existing_catalog.get("_meta", {}).get(
        "active_channels", ["email"]
    )

    try:
        with get_db_session() as db:
            # email_template
            email_rows = db.execute(
                text("""
                    SELECT template_id, display_name, category, is_active
                    FROM public.email_template
                    ORDER BY template_id
                """)
            ).fetchall()

            # notification_template (grouped by type_code)
            notif_rows = db.execute(
                text("""
                    SELECT notification_type_code,
                           array_agg(channel ORDER BY channel) AS channels
                    FROM public.notification_template
                    GROUP BY notification_type_code
                    ORDER BY notification_type_code
                """)
            ).fetchall()

            # communication_template (grouped by template_code)
            comm_rows = db.execute(
                text("""
                    SELECT template_code,
                           array_agg(channel ORDER BY channel) AS channels,
                           bool_and(is_active) AS all_active
                    FROM public.communication_template
                    GROUP BY template_code
                    ORDER BY template_code
                """)
            ).fetchall()

            # notification_channel — all known channels in the DB
            channel_rows = db.execute(
                text("SELECT code FROM public.notification_channel ORDER BY code")
            ).fetchall()

    except Exception as exc:
        print(f"❌ DB query failed: {exc}")
        return 1

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    all_channels = [r.code for r in channel_rows]

    # Preserve manually-maintained fields from the existing catalog
    existing_meta = existing_catalog.get("_meta", {})

    catalog = {
        "_meta": {
            "description": (
                "Cached template catalog for test_fire_templates.py --help display "
                "and --db-update refresh."
            ),
            "last_updated": today,
            "note": (
                "Run: python migrations/scripts/test_fire_templates.py --db-update "
                "to refresh from live DB."
            ),
            "active_channels": existing_active_channels,
            "active_channels_note": existing_meta.get(
                "active_channels_note",
                "Manually maintained. Valid values come from all_channels below. "
                "Only add a channel here when its fire logic is implemented in test_fire_templates.py.",
            ),
            "all_channels": all_channels,
            "all_channels_note": "All channels in notification_channel DB table. Auto-refreshed by --db-update. Do not edit manually.",
        },
        "email_templates": [
            {
                "template_id": r.template_id,
                "display_name": r.display_name,
                "category": r.category,
                "is_active": r.is_active,
            }
            for r in email_rows
        ],
        "notification_templates": [
            {
                "type_code": r.notification_type_code,
                "channels": list(r.channels),
            }
            for r in notif_rows
        ],
        "communication_templates": [
            {
                "template_code": r.template_code,
                "channels": list(r.channels),
                "is_active": r.all_active,
            }
            for r in comm_rows
        ],
    }

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
        f.write("\n")

    print(f"  ✅ email_template        — {len(catalog['email_templates'])} rows")
    print(
        f"  ✅ notification_template — {len(catalog['notification_templates'])} type codes"
    )
    print(
        f"  ✅ communication_template — {len(catalog['communication_templates'])} template codes"
    )
    print(f"  ✅ all_channels          — {all_channels}")
    print(
        f"  ✅ active_channels       — {existing_active_channels} (preserved from existing catalog)"
    )
    print(f"\n  Written to: {CATALOG_PATH}")
    print("  Run --help to see the updated catalog.")
    return 0


def _fire_email_template(
    template_id: str,
    recipient: str,
    tenant_id: str,
    dry_run: bool,
) -> int:
    """
    Fire an email_template by template_id.

    Returns exit code: 0 = success, 1 = error.
    """
    with get_db_session() as db:
        row = db.execute(
            text("""
                SELECT template_id, display_name, subject_template, body_html_template,
                       body_plain_template, is_active
                FROM public.email_template
                WHERE template_id = :tid
            """),
            {"tid": template_id},
        ).first()

    if row is None:
        print(f"❌ email_template '{template_id}' not found in DB.")
        return 1

    if not row.is_active:
        print(f"❌ email_template '{template_id}' is disabled (is_active=False).")
        return 1

    subject = _substitute(row.subject_template, TEST_RENDER_CONTEXT)
    body_plain = _substitute(row.body_plain_template, TEST_RENDER_CONTEXT)
    body_html = _substitute(row.body_html_template, TEST_RENDER_CONTEXT)

    print("=== test_fire_templates.py ===")
    print(f"Template type : email_template / {template_id}")
    print("Channel       : email")
    print(f"Recipient     : {recipient}")
    print(f"Tenant        : {tenant_id}")
    print(f"Dry run       : {dry_run}")
    print()
    print("[RENDERED SUBJECT]")
    print(subject)
    print()
    print("[RENDERED BODY (first 200 chars)]")
    print(body_plain[:200])
    print()

    if dry_run:
        print("[DRY RUN — not sent]")
        return 0

    print("Sending via SendGrid...")
    from services.email_service import send_email

    result = send_email(
        to=recipient,
        subject=subject,
        body=body_plain,
        html_body=body_html,
    )

    if result.get("status") == "sent":
        print(
            f"✅ Send result: {{'status': '{result['status']}', 'http_status': {result['http_status']}}}"
        )
        return 0
    else:
        print(f"❌ Send failed: {result}")
        return 1


def _fire_notification_template(
    type_code: str,
    channel: str,
    locale: str,
    recipient: str,
    tenant_id: str,
    dry_run: bool,
) -> int:
    """
    Fire a notification_template by notification_type_code + channel + locale.

    Queries platform defaults (tenant_id IS NULL) first, then tenant-specific override.
    Returns exit code: 0 = success, 1 = error.
    """
    with get_db_session() as db:
        row = db.execute(
            text("""
                SELECT notification_type_code, channel, locale, subject, body, is_active
                FROM public.notification_template
                WHERE notification_type_code = :code
                  AND channel = :channel
                  AND locale = :locale
                  AND (tenant_id IS NULL OR tenant_id = CAST(:tid AS uuid))
                ORDER BY tenant_id NULLS LAST
                LIMIT 1
            """),
            {
                "code": type_code,
                "channel": channel,
                "locale": locale,
                "tid": tenant_id,
            },
        ).first()

    if row is None:
        print(
            f"❌ notification_template not found: "
            f"type_code='{type_code}' channel='{channel}' locale='{locale}'"
        )
        return 1

    if not row.is_active:
        print(
            f"❌ notification_template '{type_code}' (channel={channel}) is disabled (is_active=False)."
        )
        return 1

    subject_raw = row.subject or f"[Notification: {type_code}]"
    body_raw = row.body

    subject = _substitute(subject_raw, TEST_RENDER_CONTEXT)
    body = _substitute(body_raw, TEST_RENDER_CONTEXT)

    print("=== test_fire_templates.py ===")
    print(f"Template type : notification_template / {type_code}")
    print(f"Channel       : {channel}")
    print(f"Recipient     : {recipient}")
    print(f"Tenant        : {tenant_id}")
    print(f"Locale        : {locale}")
    print(f"Dry run       : {dry_run}")
    print()
    print("[RENDERED SUBJECT]")
    print(subject)
    print()
    print("[RENDERED BODY (first 200 chars)]")
    print(body[:200])
    print()

    if dry_run:
        print("[DRY RUN — not sent]")
        return 0

    print("Sending via SendGrid...")
    from services.email_service import send_email

    result = send_email(
        to=recipient,
        subject=subject,
        body=body,
    )

    if result.get("status") == "sent":
        print(
            f"✅ Send result: {{'status': '{result['status']}', 'http_status': {result['http_status']}}}"
        )
        return 0
    else:
        print(f"❌ Send failed: {result}")
        return 1


def main() -> int:
    catalog = _load_catalog()
    parser = parse_args(catalog)
    args = parser.parse_args()

    # --db-update mode — no recipient required, exits immediately after update
    if args.db_update:
        return mode_db_update()

    # Channel guard — reads active_channels from catalog (no hardcoded list)
    active_channels = _get_active_channels(catalog)
    if args.channel.lower() not in active_channels:
        all_channels = catalog.get("_meta", {}).get(
            "all_channels", ["email", "in_app", "push", "sms"]
        )
        pending = [c for c in all_channels if c not in active_channels]
        active_str = ", ".join(active_channels)
        pending_str = ", ".join(pending) if pending else "none"
        print(
            f"❌ Channel '{args.channel}' is not yet supported.\n"
            f"   Active channels  : {active_str}\n"
            f"   Pending channels : {pending_str}\n"
            f"   To add support, implement the channel handler and add it to "
            f"_meta.active_channels in data/template_catalog.json."
        )
        return 1

    # --recipient is required for fire modes
    if not args.recipient:
        print(
            "❌ --recipient is required when using --email-template or --template-type."
        )
        parser.print_usage()
        return 1

    tenant_id = _get_tenant_id(args)

    if args.email_template:
        return _fire_email_template(
            template_id=args.email_template,
            recipient=args.recipient,
            tenant_id=tenant_id,
            dry_run=args.dry_run,
        )
    else:
        return _fire_notification_template(
            type_code=args.template_type,
            channel=args.channel,
            locale=args.locale,
            recipient=args.recipient,
            tenant_id=tenant_id,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    sys.exit(main())
