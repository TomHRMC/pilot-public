"""
seed_core.py — Group A: Re-inserts all Alembic-managed reference/lookup data.

Purpose: Used when restoring from a schema-only pg_dump (after `alembic stamp head`,
which skips `upgrade()` functions). On a fresh `alembic upgrade head` this script
is a no-op (all ON CONFLICT DO NOTHING).

ALL seed values verified against the live dev DB on 2026-06-01.
Updated 2026-07-06: Added 14 missing tables (SD-01).

Modes:
  --mode seed     (default) Insert all lookup rows; safe to re-run (ON CONFLICT DO NOTHING)
  --mode inspect  Show current DB state with actual values for every managed table
  --mode show     Print what would be seeded; no DB required

Usage:
  python migrations/scripts/seed_core.py
  python migrations/scripts/seed_core.py --mode inspect
  python migrations/scripts/seed_core.py --mode show
"""

import argparse
import json
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text  # noqa: E402

from migrations.scripts._db_utils import get_db_session  # noqa: E402
from migrations.scripts._env_profiles import (  # noqa: E402
    add_env_args,
    assert_group_allowed,
    assert_target_compatible,
    print_seed_banner,
    resolve_profile_from_args,
)

# ── Path to email template JSON data directory ────────────────────────────────
EMAIL_TEMPLATES_DIR = Path(__file__).parent / "data" / "email_templates"

# ── VERIFIED SEED DATA (matches live DB 2026-06-01) ───────────────────────────
#
# Table schema notes:
#   address_type, contact_type: have tenant_id (nullable)
#   taxability_code: NO tenant_id column
#   currency: code is PK, no tenant_id
#   job_status, quote_status, invoice_status, payment_status, payment_type:
#     have tenant_id (nullable), need WHERE tenant_id IS NULL for global rows
#
# ─────────────────────────────────────────────────────────────────────────────

# Tables with a 'code' PK and no tenant_id column
SIMPLE_CODE_TABLES = {
    "taxability_code": {
        "cols": ["code", "name", "description", "is_active"],
        "rows": [
            {
                "code": "taxable",
                "name": "Taxable",
                "description": "Standard sales tax applies",
                "is_active": True,
            },
            {
                "code": "exempt",
                "name": "Tax Exempt",
                "description": "No sales tax (customer has exemption certificate)",
                "is_active": True,
            },
            {
                "code": "zero_rated",
                "name": "Zero-Rated",
                "description": "0% tax rate (different from exempt for reporting)",
                "is_active": True,
            },
        ],
    },
    "currency": {
        "cols": ["code", "name", "symbol", "is_active"],
        "rows": [
            {"code": "USD", "name": "US Dollar", "symbol": "$", "is_active": True},
            {
                "code": "CAD",
                "name": "Canadian Dollar",
                "symbol": "C$",
                "is_active": False,  # SD-2: deactivated (USD-only for MVP)
            },
            {"code": "EUR", "name": "Euro", "symbol": "€", "is_active": False},  # SD-2
            {
                "code": "GBP",
                "name": "British Pound",
                "symbol": "£",
                "is_active": False,
            },  # SD-2
        ],
    },
    # webhook_event_type — code PK, no tenant_id, no id column
    "webhook_event_type": {
        "cols": ["code", "name", "is_active"],
        "rows": [
            {"code": "invoice.paid", "name": "Invoice Paid", "is_active": True},
            {"code": "job.updated", "name": "Job Updated", "is_active": True},
            {"code": "quote.accepted", "name": "Quote Accepted", "is_active": True},
        ],
    },
    # sso_provider — code PK, no tenant_id, no id column
    "sso_provider": {
        "cols": ["code", "name", "is_active"],
        "rows": [
            {"code": "google", "name": "Google", "is_active": True},
            {"code": "microsoft", "name": "Microsoft", "is_active": True},
        ],
    },
    # QB-H1: app_service_category — code PK, no tenant_id, no id column.
    # Owned by seed_core.py Group A since QB-H1 (migration ↔ seed byte-parity).
    "app_service_category": {
        "cols": ["code", "description", "is_active"],
        "rows": [
            {
                "code": "accounting",
                "description": "Accounting & Bookkeeping integrations",
                "is_active": True,
            },
        ],
    },
    # QB-H1: app_service_provider — code PK, no tenant_id, no id column.
    # Canonical provider_code is 'quickbooks' (design §G Q1).
    "app_service_provider": {
        "cols": ["code", "description", "is_active"],
        "rows": [
            {
                "code": "quickbooks",
                "description": "QuickBooks Online (Intuit)",
                "is_active": True,
            },
        ],
    },
}

# Tables with tenant_id (nullable) — global rows have tenant_id IS NULL
TENANT_NULLABLE_CODE_TABLES = {
    "address_type": {
        "cols": ["code", "name", "is_default", "is_active"],
        "rows": [
            {
                "code": "billing",
                "name": "Billing Address",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "service_location",
                "name": "Service Location",
                "is_default": True,
                "is_active": True,
            },
            {
                "code": "mailing",
                "name": "Mailing Address",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "shipping",
                "name": "Shipping Address",
                "is_default": False,
                "is_active": True,
            },
        ],
    },
    "contact_type": {
        "cols": ["code", "name", "is_default", "is_active"],
        "rows": [
            {
                "code": "primary",
                "name": "Primary Contact",
                "is_default": True,
                "is_active": True,
            },
            {
                "code": "billing",
                "name": "Billing Contact",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "technical",
                "name": "Technical Contact",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "decision_maker",
                "name": "Decision Maker",
                "is_default": False,
                "is_active": True,
            },
        ],
    },
    "job_status": {
        "cols": ["code", "name", "is_default", "is_terminal", "is_active"],
        "rows": [
            {
                "code": "draft",
                "name": "Draft",
                "is_default": True,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "scheduled",
                "name": "Scheduled",
                "is_default": False,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "in_progress",
                "name": "In Progress",
                "is_default": False,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "completed",
                "name": "Completed",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            {
                "code": "cancelled",
                "name": "Cancelled",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
        ],
    },
    "quote_status": {
        "cols": ["code", "name", "is_default", "is_terminal", "is_active"],
        "rows": [
            {
                "code": "draft",
                "name": "Draft",
                "is_default": True,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "pending",
                "name": "Pending Review",
                "is_default": False,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "pending_approval",
                "name": "Pending Approval",
                "is_default": False,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "sent",
                "name": "Sent to Customer",
                "is_default": False,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "approved",
                "name": "Approved",
                "is_default": False,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "accepted",
                "name": "Accepted",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            {
                "code": "rejected",
                "name": "Rejected",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            {
                "code": "expired",
                "name": "Expired",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            {
                "code": "converted",
                "name": "Converted to Job",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            # SD-2: void added
            {
                "code": "void",
                "name": "Void",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
        ],
    },
    "invoice_status": {
        "cols": ["code", "name", "is_default", "is_terminal", "is_active"],
        "rows": [
            {
                "code": "draft",
                "name": "Draft",
                "is_default": True,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "issued",
                "name": "Issued",
                "is_default": False,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "paid",
                "name": "Paid",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            {
                "code": "void",
                "name": "Void",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            {
                "code": "writeoff",
                "name": "Write-off",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            # SD-2: partial added
            {
                "code": "partial",
                "name": "Partially Paid",
                "is_default": False,
                "is_terminal": False,
                "is_active": True,
            },
        ],
    },
    "payment_status": {
        "cols": ["code", "name", "is_default", "is_terminal", "is_active"],
        "rows": [
            {
                "code": "pending",
                "name": "Pending",
                "is_default": True,
                "is_terminal": False,
                "is_active": True,
            },
            {
                "code": "succeeded",
                "name": "Succeeded",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            {
                "code": "failed",
                "name": "Failed",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            {
                "code": "canceled",
                "name": "Canceled",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
            # SD-2: refunded added
            {
                "code": "refunded",
                "name": "Refunded",
                "is_default": False,
                "is_terminal": True,
                "is_active": True,
            },
        ],
    },
    "payment_type": {
        "cols": ["code", "name", "is_active"],
        "rows": [
            {"code": "card", "name": "Card", "is_active": True},
            {"code": "ach", "name": "ACH", "is_active": True},
            {"code": "bank_debit", "name": "Bank Debit", "is_active": True},
            {"code": "manual_check", "name": "Manual Check", "is_active": True},
            {"code": "venmo", "name": "Venmo", "is_active": True},
            {"code": "wallet", "name": "Wallet", "is_active": True},
        ],
    },
    "tenant_user_status": {
        "cols": ["code", "name", "is_default", "is_active"],
        "rows": [
            {"code": "active", "name": "Active", "is_default": True, "is_active": True},
            {
                "code": "invited",
                "name": "Invited",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "pending",
                "name": "Pending",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "suspended",
                "name": "Suspended",
                "is_default": False,
                "is_active": True,
            },
        ],
    },
    "customer_lifecycle_status": {
        "cols": ["code", "name", "is_default", "is_active"],
        "rows": [
            {"code": "active", "name": "Active", "is_default": True, "is_active": True},
            {
                "code": "prospect",
                "name": "Prospect",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "dormant",
                "name": "Dormant",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "churned",
                "name": "Churned",
                "is_default": False,
                "is_active": True,
            },
        ],
    },
    "site_lifecycle_status": {
        "cols": ["code", "name", "is_default", "is_active"],
        "rows": [
            {"code": "active", "name": "Active", "is_default": True, "is_active": True},
            {
                "code": "closed",
                "name": "Closed",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "construction",
                "name": "Construction",
                "is_default": False,
                "is_active": True,
            },
        ],
    },
    "supplier_lifecycle_status": {
        "cols": ["code", "name", "is_default", "is_active"],
        "rows": [
            {"code": "active", "name": "Active", "is_default": True, "is_active": True},
            {
                "code": "deprecated",
                "name": "Deprecated",
                "is_default": False,
                "is_active": True,
            },
        ],
    },
    "notification_type": {
        "cols": ["code", "name", "audience", "is_active"],
        "rows": [
            {
                "code": "customer_communication_sent",
                "name": "Customer Communication Sent",
                "audience": "tenant",
                "is_active": True,
            },
            {
                "code": "dunning_reminder",
                "name": "Dunning Reminder",
                "audience": "tenant",
                "is_active": True,
            },
            {
                "code": "quote_accepted",
                "name": "Quote Accepted",
                "audience": "tenant",
                "is_active": True,
            },
            # SD-2: 6 new notification types
            {
                "code": "job_assigned",
                "name": "Job Assigned",
                "audience": "tenant",
                "is_active": True,
            },
            {
                "code": "schedule_changed",
                "name": "Schedule Changed",
                "audience": "tenant",
                "is_active": True,
            },
            {
                "code": "qb_sync_conflict",
                "name": "QB Sync Conflict",
                "audience": "tenant",
                "is_active": True,
            },
            {
                "code": "qb_conflict_pre_warning",
                "name": "QB Conflict Pre-Warning",
                "audience": "tenant",
                "is_active": True,
            },
            # QB-H1: connection-expiry notification (owner email/in_app/push)
            {
                "code": "qb_connection_expired",
                "name": "QuickBooks Connection Expired",
                "audience": "tenant",
                "is_active": True,
            },
            # STRIPE-CONNECT-1: Connect disconnect + dispute owner notifications
            # (byte-identical to migration d038d647ec41)
            {
                "code": "stripe_connect_disconnected",
                "name": "Stripe Connect Disconnected",
                "audience": "tenant",
                "is_active": True,
            },
            {
                "code": "stripe_dispute_opened",
                "name": "Stripe Dispute Opened",
                "audience": "tenant",
                "is_active": True,
            },
            {
                "code": "gps_variance_alert",
                "name": "GPS Variance Alert",
                "audience": "tenant",
                "is_active": True,
            },
            {
                "code": "system_template_updated",
                "name": "System Template Updated",
                "audience": "tenant",
                "is_active": True,
            },
            # C-B6: Charter free-period notification schedule (T-30/14/7/3/1/0)
            {
                "code": "free_period_warning",
                "name": "Free Period Warning",
                "audience": "tenant",
                "is_active": True,
            },
        ],
    },
    # quote_link_status — has tenant_id (nullable), StandardAuditMixin (created_at/updated_at NOT NULL, no server default)
    "quote_link_status": {
        "cols": ["code", "name", "is_default", "is_active"],
        "rows": [
            {"code": "active", "name": "Active", "is_default": True, "is_active": True},
            {
                "code": "exhausted",
                "name": "Max Uses Reached",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "expired",
                "name": "Expired",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "revoked",
                "name": "Revoked",
                "is_default": False,
                "is_active": True,
            },
        ],
    },
    # supplier_item_category — has tenant_id (nullable), StandardAuditMixin
    "supplier_item_category": {
        "cols": ["code", "name", "is_active"],
        "rows": [
            {
                "code": "conduit_raceway",
                "name": "Conduit, Raceway & Strut",
                "is_active": True,
            },
            {
                "code": "dist_equip",
                "name": "Distribution & Control (Breakers/Panels)",
                "is_active": True,
            },
            {"code": "enclosures", "name": "Boxes & Enclosures", "is_active": True},
            {"code": "fasteners", "name": "Hardware & Fasteners", "is_active": True},
            {"code": "fittings", "name": "Fittings", "is_active": True},
            {"code": "lighting", "name": "Lighting & Controls", "is_active": True},
            {
                "code": "tools_equip",
                "name": "Tools & Field Equipment",
                "is_active": True,
            },
            {"code": "wire_cable", "name": "Wire & Cable", "is_active": True},
            {
                "code": "wiring_devices",
                "name": "Wiring Devices (Switches/Outlets)",
                "is_active": True,
            },
        ],
    },
    # supplier_item_uom — has tenant_id (nullable), StandardAuditMixin
    "supplier_item_uom": {
        "cols": ["code", "name", "is_default", "is_active"],
        "rows": [
            {"code": "bag", "name": "Bag", "is_default": False, "is_active": True},
            {"code": "box", "name": "Box", "is_default": False, "is_active": True},
            {"code": "each", "name": "Each", "is_default": True, "is_active": True},
            {"code": "foot", "name": "Foot", "is_default": False, "is_active": True},
            {
                "code": "linear_foot",
                "name": "Linear Foot",
                "is_default": False,
                "is_active": True,
            },
            {
                "code": "package",
                "name": "Package",
                "is_default": False,
                "is_active": True,
            },
            {"code": "roll", "name": "Roll", "is_default": False, "is_active": True},
            {"code": "spool", "name": "Spool", "is_default": False, "is_active": True},
        ],
    },
}

# notification_channel has NO tenant_id — kept in SIMPLE_CODE_TABLES below
NOTIFICATION_CHANNEL_DEF = {
    "cols": ["code", "name", "is_active"],
    "rows": [
        {"code": "email", "name": "Email", "is_active": True},
        {"code": "sms", "name": "SMS", "is_active": True},
        {"code": "push", "name": "Push", "is_active": True},
        {"code": "in_app", "name": "In-App", "is_active": True},
    ],
}

# Special tables with different structure
ENTITY_TYPE_ROWS = [
    {"code": "customer", "name": "Customer"},
    {"code": "site", "name": "Site"},
    {"code": "job", "name": "Job"},
    {"code": "quote", "name": "Quote"},
    {"code": "invoice", "name": "Invoice"},
    {"code": "customer_communication", "name": "Customer Communication"},
    # C-B6: Required FK target for NotificationEvent.entity_type_code on free-period events
    {"code": "tenant", "name": "Tenant"},
]

PLATFORM_ROLE_ROWS = [
    {"code": "owner", "name": "Owner"},
    {"code": "accountant", "name": "Accountant"},
    {"code": "support", "name": "Support"},
]

# job_expense_category — no tenant_id, no is_default
JOB_EXPENSE_CATEGORY_ROWS = [
    {"code": "materials", "name": "Materials & Supplies", "is_active": True},
    {"code": "equipment", "name": "Equipment Rental", "is_active": True},
    {"code": "permits", "name": "Permits & Fees", "is_active": True},
]

# qpl_contact_action_type — live values
QPL_CONTACT_ACTION_ROWS = [
    {"code": "approve", "name": "Approve"},
    {"code": "message", "name": "Message"},
    {"code": "request_change", "name": "Request Change"},
    {"code": "view", "name": "View"},
]

# NOTE: subscription_status is managed by test fixtures (conftest.py) and
# Alembic migrations — do NOT seed it here. Seeding caused stripe tests to fail
# because the test fixture creates its own 'active' row with a fresh UUID.

# notification_category
NOTIFICATION_CATEGORY_ROWS = [
    {
        "code": "quote_approvals",
        "display_label": "Quote Approvals",
        "description": "Notifications when quotes are submitted, approved, or rejected.",
        "display_order": 1,
    },
    {
        "code": "field_issues",
        "display_label": "Field Issues",
        "description": "Notifications for field escalations and mobile sync conflicts.",
        "display_order": 2,
    },
    {
        "code": "sync_conflicts",
        "display_label": "Sync Conflicts",
        "description": "Notifications for QuickBooks and calendar sync conflicts.",
        "display_order": 3,
    },
    {
        "code": "job_activity",
        "display_label": "Job Activity",
        "description": "Notifications for job assignments, updates, and status changes.",
        "display_order": 4,
    },
    {
        "code": "customer_activity",
        "display_label": "Customer Activity",
        "description": "Notifications for customer communications and inbound messages.",
        "display_order": 5,
    },
    {
        "code": "billing",
        "display_label": "Billing",
        "description": "Notifications for invoice activity, payments, and subscription changes.",
        "display_order": 6,
    },
    {
        "code": "background_sync_alerts",
        "display_label": "Background Sync Alerts",
        "description": "Notifications for background synchronization status and errors.",
        "display_order": 7,
    },
    {
        "code": "system_announcements",
        "display_label": "System Announcements",
        "description": "Platform announcements and critical system notifications.",
        "display_order": 8,
    },
]

# notification_default_policy (24 rows — from live DB)
NOTIFICATION_DEFAULT_POLICY_ROWS = [
    {"category_id": "quote_approvals", "channel": "email", "enabled": True},
    {"category_id": "quote_approvals", "channel": "in_app", "enabled": True},
    {"category_id": "quote_approvals", "channel": "push", "enabled": True},
    {"category_id": "field_issues", "channel": "email", "enabled": True},
    {"category_id": "field_issues", "channel": "in_app", "enabled": True},
    {"category_id": "field_issues", "channel": "push", "enabled": True},
    {"category_id": "sync_conflicts", "channel": "email", "enabled": True},
    {"category_id": "sync_conflicts", "channel": "in_app", "enabled": True},
    {"category_id": "sync_conflicts", "channel": "push", "enabled": False},
    {"category_id": "job_activity", "channel": "email", "enabled": False},
    {"category_id": "job_activity", "channel": "in_app", "enabled": True},
    {"category_id": "job_activity", "channel": "push", "enabled": True},
    {"category_id": "customer_activity", "channel": "email", "enabled": False},
    {"category_id": "customer_activity", "channel": "in_app", "enabled": True},
    {"category_id": "customer_activity", "channel": "push", "enabled": True},
    {"category_id": "billing", "channel": "email", "enabled": True},
    {"category_id": "billing", "channel": "in_app", "enabled": True},
    {"category_id": "billing", "channel": "push", "enabled": False},
    {"category_id": "background_sync_alerts", "channel": "email", "enabled": False},
    {"category_id": "background_sync_alerts", "channel": "in_app", "enabled": True},
    {"category_id": "background_sync_alerts", "channel": "push", "enabled": True},
    {"category_id": "system_announcements", "channel": "email", "enabled": True},
    {"category_id": "system_announcements", "channel": "in_app", "enabled": True},
    {"category_id": "system_announcements", "channel": "push", "enabled": False},
]

# tax_rate_version (AppendOnly — no updated_at; valid_period is tstzrange, not daterange)
# Idempotency: skip if jurisdiction_code + rate_pct already exists
TAX_RATE_VERSION_ROWS = [
    {
        "jurisdiction_code": "US-DEFAULT",
        "description": "Default US Sales Tax",
        "rate_pct": "6.0",
        "valid_period": "[2020-01-01,)",
    },
    {
        "jurisdiction_code": "US-TX-HARRIS",
        "description": "Harris County, TX Combined Rate",
        "rate_pct": "8.25",
        "valid_period": "[2024-01-01,)",
    },
    {
        "jurisdiction_code": "US-CA-LA",
        "description": "Los Angeles County, CA",
        "rate_pct": "9.5",
        "valid_period": "[2024-01-01,)",
    },
]

# ── NEW SD-01 Tables ─────────────────────────────────────────────────────────

# notification_category_sub_trigger — code PK (text), no id, no tenant_id
# NOTE: has server defaults on created_at/updated_at — no need to include explicitly
NOTIFICATION_CATEGORY_SUB_TRIGGER_ROWS = [
    {
        "code": "customer_activity.inbound_sms_reply",
        "category_id": "customer_activity",
        "display_label": "Inbound SMS Reply",
        "forced_minimum_push_uniform": False,
        "forced_minimum_push_recipient_only": True,
    },
    {
        "code": "field_issues.all",
        "category_id": "field_issues",
        "display_label": "All Field Issues",
        "forced_minimum_push_uniform": True,
        "forced_minimum_push_recipient_only": False,
    },
    {
        "code": "job_activity.assignment",
        "category_id": "job_activity",
        "display_label": "Job Assignment",
        "forced_minimum_push_uniform": False,
        "forced_minimum_push_recipient_only": True,
    },
    {
        "code": "mfa_grace_reminder_critical",
        "category_id": "system_announcements",
        "display_label": "MFA Grace Reminder (Critical — Day 7)",
        "forced_minimum_push_uniform": True,
        "forced_minimum_push_recipient_only": True,
    },
    {
        "code": "mfa_grace_reminder_gentle",
        "category_id": "system_announcements",
        "display_label": "MFA Grace Reminder (Gentle — Days 0-3)",
        "forced_minimum_push_uniform": False,
        "forced_minimum_push_recipient_only": False,
    },
    {
        "code": "mfa_grace_reminder_urgent",
        "category_id": "system_announcements",
        "display_label": "MFA Grace Reminder (Urgent — Days 4-6)",
        "forced_minimum_push_uniform": False,
        "forced_minimum_push_recipient_only": False,
    },
    {
        "code": "system_announcements.critical",
        "category_id": "system_announcements",
        "display_label": "Critical Announcements",
        "forced_minimum_push_uniform": True,
        "forced_minimum_push_recipient_only": False,
    },
]

# product_feature — code PK, no tenant_id, StandardAuditMixin (created_at/updated_at NOT NULL, no server default)
# SD-07: qb_sync_operations removed (QB sync is unlimited on all tiers per GTM matrix)
# SD-07: dispatch_slots and outbound_sms_segments added
# MKT-B11: dispatch_slots → schedule_lanes rename. ppfv references updated to schedule_lanes.
#           dispatch_slots row is cleaned up by mode_seed() DELETE below.
# SD-2: data_exports removed (orphaned row — not metered for billing)
PRODUCT_FEATURE_ROWS = [
    {
        "code": "schedule_lanes",
        "name": "Schedule Lanes",
        "unit": "lanes",
        "description": "Maximum concurrent dispatch schedule lanes on the board",
    },
    {
        "code": "outbound_sms_segments",
        "name": "Outbound SMS Segments",
        "unit": "segments",
        "description": "Outbound SMS segments per billing cycle",
    },
    {
        "code": "voice_ai_minutes",
        "name": "Voice AI minutes",
        "unit": "minutes",
        "description": "Minutes spent processing voice commands via Whisper/Ollama",
    },
]

# Orphaned product_feature rows to remove during seed (MKT-B11 rename left dispatch_slots behind)
PRODUCT_FEATURE_CLEANUP_CODES = ["dispatch_slots", "data_exports", "qb_sync_operations"]

# jwk_status — AppendOnly (created_at only, no updated_at), no tenant_id, id UUID PK
JWK_STATUS_ROWS = [
    {"code": "active", "name": "Active", "is_default": True, "is_signable": True},
    {"code": "retired", "name": "Retired", "is_default": False, "is_signable": False},
    {"code": "retiring", "name": "Retiring", "is_default": False, "is_signable": False},
]

# tenant_user_role — code PK, no tenant_id, StandardAuditMixin (created_at/updated_at NOT NULL, no server default)
# permissions is JSONB — stored as JSON array
TENANT_USER_ROLE_ROWS = [
    {
        "code": "accountant",
        "name": "Accountant",
        "description": "Read-only access to financial data and audit logs for compliance and bookkeeping.",
        "permissions": [
            "audit.view",
            "dashboard.manage",
            "reports.view",
            "*.view",
            "catalog.manage",
            # PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): schedule read —
            # view jobs' technician assignments + read-only dispatch board.
            # Write stays schedule.manage (owner/office_staff only).
            "schedule.view_all",
            # PLP-FIX-9: self-service Security-page grants (INV-BUG-8)
            "mfa.enroll_self",
            "account.session.view_own",
            "account.session.revoke_own",
            "help_chat.delete_own_history",
        ],
        "is_default": False,
        "is_active": True,
    },
    {
        "code": "office_staff",
        "name": "Office Staff",
        "description": "Manages customers, quotes, sites, and administrative tasks. Cannot access financial or job execution data.",
        "permissions": [
            "addresses.*",
            "contacts.*",
            "customers.*",
            "invoices.create",
            "invoices.view",
            "jobs.view",
            "quotes.*",
            "reports.view",
            "sites.*",
            "users.view",
            "schedule.manage",
            "schedule.view_all",
            "dashboard.manage",
            # PLP-FIX-9: communications grants (INV-D-5) + self-service Security-page grants (INV-BUG-8)
            "communications.view",
            "communications.send",
            "mfa.enroll_self",
            "account.session.view_own",
            "account.session.revoke_own",
            "help_chat.delete_own_history",
        ],
        "is_default": False,
        "is_active": True,
    },
    {
        "code": "owner",
        "name": "Owner",
        "description": "Full access to all tenant resources. Recommended for solo contractors and business owners.",
        "permissions": [
            "*",
            "users.manage",
            "users.view",
            "integrations.manage",
            "jobs.loto_confirm",
        ],
        "is_default": True,
        "is_active": True,
    },
    {
        "code": "technician",
        "name": "Field Technician",
        "description": "Can view and update jobs, log time and expenses, use voice AI for field operations.",
        "permissions": [
            "dashboard.manage",
            "expenses.create",
            "expenses.update",
            "expenses.view",
            "jobs.update",
            "jobs.view",
            "mobile_sync.resolve",
            "mobile_sync.view",
            "nec.calculate",
            "schedule.view_own",
            "time_entries.create",
            "time_entries.update",
            "time_entries.view",
            "voice.create",
            "voice.use",
            "voice.view",
            "jobs.loto_confirm",
            # PLP-FIX-9: self-service Security-page grants (INV-BUG-8)
            "mfa.enroll_self",
            "account.session.view_own",
            "account.session.revoke_own",
            "help_chat.delete_own_history",
        ],
        "is_default": False,
        "is_active": True,
    },
]

# sync_conflict_classification_matrix — has server defaults on created_at/updated_at
# id has gen_random_uuid() default. Unique on (operation_type, trigger_condition) effectively.
SYNC_CONFLICT_MATRIX_ROWS = [
    {
        "operation_type": "change_order",
        "trigger_condition": "quote_version_active",
        "severity": "auto_silent",
        "classification_reason": "Quote version is still active",
    },
    {
        "operation_type": "change_order",
        "trigger_condition": "quote_version_superseded",
        "severity": "tech_resolvable",
        "classification_reason": "Quote version superseded since capture",
    },
    {
        "operation_type": "expense",
        "trigger_condition": "category_exists_under_limit",
        "severity": "auto_silent",
        "classification_reason": "Expense category exists and is under limit",
    },
    {
        "operation_type": "expense",
        "trigger_condition": "category_renamed",
        "severity": "auto_notice",
        "classification_reason": "Expense category was renamed server-side",
    },
    {
        "operation_type": "expense",
        "trigger_condition": "exceeds_per_item_limit",
        "severity": "tech_resolvable",
        "classification_reason": "Expense exceeds tenant per-item limit",
    },
    {
        "operation_type": "expense",
        "trigger_condition": "job_deleted",
        "severity": "owner_escalation",
        "classification_reason": "Job deleted while expense was captured",
    },
    {
        "operation_type": "loto_check",
        "trigger_condition": "job_completed_before_sync",
        "severity": "auto_notice",
        "classification_reason": "Job completed before LOTO sync arrived",
    },
    {
        "operation_type": "loto_check",
        "trigger_condition": "job_in_progress",
        "severity": "auto_silent",
        "classification_reason": "Job still in progress when LOTO synced",
    },
    {
        "operation_type": "photo",
        "trigger_condition": "job_deleted",
        "severity": "owner_escalation",
        "classification_reason": "Job deleted while photo was captured",
    },
    {
        "operation_type": "photo",
        "trigger_condition": "job_exists",
        "severity": "auto_silent",
        "classification_reason": "Job exists and photo uploaded cleanly",
    },
    {
        "operation_type": "photo",
        "trigger_condition": "storage_limit_exceeded",
        "severity": "tech_resolvable",
        "classification_reason": "Storage limit exceeded",
    },
    {
        "operation_type": "status_change",
        "trigger_condition": "job_already_completed",
        "severity": "owner_escalation",
        "classification_reason": "Job already completed by another tech",
    },
    {
        "operation_type": "status_change",
        "trigger_condition": "normal_transition",
        "severity": "auto_silent",
        "classification_reason": "Normal job status transition",
    },
    {
        "operation_type": "time_entry",
        "trigger_condition": "job_deleted",
        "severity": "owner_escalation",
        "classification_reason": "Job deleted while you worked it",
    },
    {
        "operation_type": "time_entry",
        "trigger_condition": "job_reassigned",
        "severity": "tech_resolvable",
        "classification_reason": "Job reassigned to different tech",
    },
    {
        "operation_type": "time_entry",
        "trigger_condition": "job_still_assigned",
        "severity": "auto_silent",
        "classification_reason": "Job still assigned to you",
    },
    {
        "operation_type": "time_entry",
        "trigger_condition": "time_overlap",
        "severity": "tech_resolvable",
        "classification_reason": "Time overlaps an existing entry",
    },
]

# communication_template — has id (gen_random_uuid default), tenant_id (nullable),
# server defaults on created_at/updated_at. Natural key: (template_code, channel, tenant_id IS NULL)
COMMUNICATION_TEMPLATE_ROWS = [
    {
        "template_code": "appointment_reminder_1h",
        "channel": "email",
        "subject": "Your Appointment Is In About 1 Hour",
        "body_template": "Hi {{customer_first_name}},\n\n{{tenant_name}} will be arriving at {{site_address}} around {{appointment_time}}.\n\nThank you,\n{{tenant_name}}",
    },
    {
        "template_code": "appointment_reminder_1h",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: {{tenant_name}} is on the way — arriving around {{appointment_time}}. Reply STOP to opt out.",
    },
    {
        "template_code": "appointment_reminder_24h",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Reminder: {{tenant_name}} appointment tomorrow at {{appointment_time}}. Reply STOP to opt out.",
    },
    {
        "template_code": "appointment_reminder_24h",
        "channel": "email",
        "subject": "Appointment Reminder — {{appointment_time}}",
        "body_template": "Hi {{customer_first_name}},\n\nThis is a reminder that {{tenant_name}} has an appointment scheduled for {{appointment_time}}.\n\nAddress: {{site_address}}\n\nThank you,\n{{tenant_name}}",
    },
    {
        "template_code": "arrived",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Hi {{ customer_first_name }}, {{ sender_name }} here — I've arrived and am starting work. Reply STOP to opt out.",
    },
    {
        "template_code": "confirm_appointment",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Hi {{ customer_first_name }}, please confirm your appointment for {{ date_time }} at {{ site_address }}. Reply YES to confirm or call us. Reply STOP to opt out.",
    },
    {
        "template_code": "invoice_sent",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Your invoice is ready. View and pay at {{invoice_link}}. Reply STOP to opt out.",
    },
    {
        "template_code": "invoice_sent",
        "channel": "email",
        "subject": "Your Invoice from {{tenant_name}}",
        "body_template": "Hi {{customer_first_name}},\n\nYour invoice for {{job_title}} is ready. View and pay here: {{invoice_link}}\n\nThank you,\n{{tenant_name}}",
    },
    {
        "template_code": "job_complete",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Hi {{ customer_first_name }}, {{ sender_name }} here — work is complete. Invoice to follow. Reply STOP to opt out.",
    },
    {
        "template_code": "on_my_way",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Hi {{ customer_first_name }}, this is {{ sender_name }} — I'm on my way, ETA {{ eta }}. Reply STOP to opt out.",
    },
    {
        "template_code": "on_my_way",
        "channel": "email",
        "subject": "On my way — ETA {{ eta }}",
        "body_template": "Hi {{ customer_first_name }},\n\nI'm on my way to {{ site_address }}. ETA {{ eta }}.\n\n{{ sender_name }}",
    },
    {
        "template_code": "parts_delay",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Hi {{ customer_first_name }}, {{ sender_name }} here — there's a parts delay. I'll update you as soon as I have more info. Reply STOP to opt out.",
    },
    {
        "template_code": "payment_received",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Payment received — thank you! {{tenant_name}} has processed your payment of {{payment_amount}}. Reply STOP to opt out.",
    },
    {
        "template_code": "payment_received",
        "channel": "email",
        "subject": "Payment Received — Thank You!",
        "body_template": "Hi {{customer_first_name}},\n\nWe have received your payment of {{payment_amount}} for {{job_title}}. Thank you for your business!\n\n{{tenant_name}}",
    },
    {
        "template_code": "running_late",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Hi {{ customer_first_name }}, {{ sender_name }} here — running about {{ minutes_late }} minutes behind. Apologies for the delay. Reply STOP to opt out.",
    },
    {
        "template_code": "recurring_job_scheduled",
        "channel": "sms",
        "subject": None,
        "body_template": "Pilot for Trades: Hi {{customer_name}}, your scheduled {{service_description}} with {{company_name}} is confirmed for {{scheduled_date}} at {{scheduled_time}}. Reply STOP to opt out.",
    },
    # SEED-FIX-1: B21 email variant (migration b1bd90914b77 ownership
    # transferred to seed_core.py — post-schema-restore recovery path).
    {
        "template_code": "recurring_job_scheduled",
        "channel": "email",
        "subject": "Your {{service_description}} is scheduled",
        "body_template": (
            "Hi {{customer_name}},\n\n"
            "Your scheduled {{service_description}} with {{company_name}} is confirmed.\n\n"
            "Date: {{scheduled_date}}\n"
            "Time: {{scheduled_time}}\n"
            "Address: {{site_address}}\n\n"
            "If you need to reschedule, please contact us at {{company_phone}}.\n\n"
            "Thank you,\n"
            "{{company_name}}"
        ),
    },
]

# platform_setting_catalog — key PK, has server defaults on created_at/updated_at
# 42 rows verified from live DB 2026-07-06
PLATFORM_SETTING_CATALOG_ROWS = [
    {
        "key": "background_sync_battery_floor_pct",
        "label": "Background sync battery floor (%)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "sync",
        "sort_order": 60,
    },
    {
        "key": "background_sync_enabled",
        "label": "Background sync enabled",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": True,
        "category": "sync",
        "sort_order": 40,
    },
    {
        "key": "background_sync_push_interval_minutes",
        "label": "Background sync push interval (minutes)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "sync",
        "sort_order": 70,
    },
    {
        "key": "background_sync_wifi_only",
        "label": "Background sync on WiFi only",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "sync",
        "sort_order": 50,
    },
    {
        "key": "calendar_conflict_auto_expire_days",
        "label": "Calendar conflict auto-expiry period (days)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "sync",
        "sort_order": 20,
    },
    {
        "key": "calendar_conflict_auto_expire_enabled",
        "label": "Calendar conflict auto-expiry enabled",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "sync",
        "sort_order": 10,
    },
    {
        "key": "calendar_conflict_pre_warning_days",
        "label": "Calendar conflict pre-warning (days)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "sync",
        "sort_order": 30,
    },
    {
        "key": "default_billable_labor_rate_cents",
        "label": "Default billable labor rate (cents/hour)",
        "value_type": "integer",
        "tenant_editable": False,
        "allows_user_override": False,
        "category": "labor",
        "sort_order": 20,
    },
    {
        "key": "default_invoice_terms_days",
        "label": "Default invoice terms (days)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "quotes",
        "sort_order": 40,
    },
    {
        "key": "default_labor_rate_cents",
        "label": "Default labor rate (cents/hour)",
        "value_type": "integer",
        "tenant_editable": False,
        "allows_user_override": False,
        "category": "labor",
        "sort_order": 10,
    },
    {
        "key": "default_quote_validity_days",
        "label": "Default quote validity (days)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "quotes",
        "sort_order": 30,
    },
    {
        "key": "default_trial_length_days",
        "label": "Default trial length (days)",
        "value_type": "integer",
        "tenant_editable": False,
        "allows_user_override": False,
        "category": "trial",
        "sort_order": 10,
    },
    {
        "key": "etc_variance_note_required_pct",
        "label": "ETC variance note required threshold (%)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "reports",
        "sort_order": 20,
    },
    {
        "key": "etc_variance_owner_notify_pct",
        "label": "ETC variance owner notify threshold (%)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "reports",
        "sort_order": 10,
    },
    {
        "key": "gps_variance_alert_threshold_meters",
        "label": "GPS variance alert threshold (meters)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "safety",
        "sort_order": 10,
    },
    {
        "key": "loto_confirmation_required",
        "label": "LOTO Confirmation Required",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "safety",
        "sort_order": 10,
    },
    {
        "key": "margin_bucket_boundaries",
        "label": "Margin bucket boundaries",
        "value_type": "jsonb",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "reports",
        "sort_order": 40,
    },
    {
        "key": "margin_target_pct",
        "label": "Margin target (%)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "reports",
        "sort_order": 30,
    },
    {
        "key": "max_discount_pct_owner",
        "label": "Maximum discount percentage",
        "value_type": "decimal",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "quotes",
        "sort_order": 20,
    },
    {
        "key": "offline_hard_limit_hours",
        "label": "Offline hard limit (hours)",
        "value_type": "integer",
        "tenant_editable": False,
        "allows_user_override": False,
        "category": "mobile",
        "sort_order": 30,
    },
    {
        "key": "photo_local_retention_days",
        "label": "Photo local retention (days)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "mobile",
        "sort_order": 20,
    },
    {
        "key": "photo_upload_wifi_only",
        "label": "Upload photos on WiFi only",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "mobile",
        "sort_order": 10,
    },
    {
        "key": "qb_auto_expire_customer_direction",
        "label": "QB customer conflict auto-expiry direction",
        "value_type": "string",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 40,
    },
    {
        "key": "qb_auto_expire_customer_enabled",
        "label": "QB customer conflict auto-expiry enabled",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 30,
    },
    {
        "key": "qb_auto_expire_days",
        "label": "QB conflict auto-expiry period (days)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 10,
    },
    {
        "key": "qb_auto_expire_expense_direction",
        "label": "QB expense conflict auto-expiry direction",
        "value_type": "string",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 100,
    },
    {
        "key": "qb_auto_expire_expense_enabled",
        "label": "QB expense conflict auto-expiry enabled",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 90,
    },
    {
        "key": "qb_auto_expire_invoice_direction",
        "label": "QB invoice conflict auto-expiry direction",
        "value_type": "string",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 80,
    },
    {
        "key": "qb_auto_expire_invoice_enabled",
        "label": "QB invoice conflict auto-expiry enabled",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 70,
    },
    {
        "key": "qb_auto_expire_quote_direction",
        "label": "QB quote conflict auto-expiry direction",
        "value_type": "string",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 60,
    },
    {
        "key": "qb_auto_expire_quote_enabled",
        "label": "QB quote conflict auto-expiry enabled",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 50,
    },
    {
        "key": "qb_pre_warning_days",
        "label": "QB conflict pre-warning (days)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "qb",
        "sort_order": 20,
    },
    {
        "key": "report_chart_threshold",
        "label": "Report chart threshold (rows)",
        "value_type": "integer",
        "tenant_editable": False,
        "allows_user_override": False,
        "category": "reports",
        "sort_order": 50,
    },
    {
        "key": "require_approval_for_tech_quotes",
        "label": "Require approval for tech quotes",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "quotes",
        "sort_order": 10,
    },
    {
        "key": "sms_quota_cap_policy",
        "label": "SMS quota cap policy",
        "value_type": "string",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "notifications",
        "sort_order": 100,
    },
    {
        "key": "tech_color_palette",
        "label": "Tech color palette",
        "value_type": "jsonb",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "reports",
        "sort_order": 60,
    },
    {
        "key": "tenant_mfa_grace_period_days",
        "label": "MFA grace period (days)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "security",
        "sort_order": 20,
    },
    {
        "key": "tenant_mfa_required",
        "label": "Require MFA for all users",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "security",
        "sort_order": 10,
    },
    {
        "key": "tenant_sync_indicator_pending_amber_threshold",
        "label": "Sync indicator amber threshold (pending items)",
        "value_type": "integer",
        "tenant_editable": False,
        "allows_user_override": False,
        "category": "sync",
        "sort_order": 80,
    },
    {
        "key": "voice_offline_audio_storage_limit_mb",
        "label": "Voice audio offline storage limit (MB)",
        "value_type": "integer",
        "tenant_editable": False,
        "allows_user_override": False,
        "category": "mobile",
        "sort_order": 40,
    },
    {
        "key": "voice_persona_tone",
        "label": "Voice AI persona tone",
        "value_type": "string",
        "tenant_editable": True,
        "allows_user_override": True,
        "category": "voice",
        "sort_order": 10,
    },
    {
        "key": "voice_persona_tone_user_override_allowed",
        "label": "Allow per-user voice persona override",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "voice",
        "sort_order": 20,
    },
    # SD-06B: Invoice reminder schedule keys
    {
        "key": "invoice_reminder_days_1",
        "label": "First invoice reminder (days overdue)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "billing",
        "sort_order": 110,
    },
    {
        "key": "invoice_reminder_days_2",
        "label": "Second invoice reminder (days overdue)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "billing",
        "sort_order": 120,
    },
    {
        "key": "invoice_reminder_days_3",
        "label": "Final invoice reminder (days overdue)",
        "value_type": "integer",
        "tenant_editable": True,
        "allows_user_override": False,
        "category": "billing",
        "sort_order": 130,
    },
    # SEED-FIX-1: B20 invoice-builder keys (migration f7f30492c3e4 ownership
    # transferred to seed_core.py — post-schema-restore recovery path).
    {
        "key": "square_integration_enabled",
        "label": "Square payment integration enabled",
        "description": "When enabled, tenants can require card-on-file via Square before work begins.",
        "value_type": "boolean",
        "tenant_editable": True,
        "allows_user_override": False,
        "allowed_values": None,
        "category": "billing",
        "sort_order": 100,
    },
    {
        "key": "default_payment_terms",
        "label": "Default invoice payment terms",
        "description": "When invoice.payment_terms is NULL, the invoice builder pre-selects this value.",
        "value_type": "string",
        "tenant_editable": True,
        "allows_user_override": False,
        "allowed_values": ["due_on_receipt", "net_15", "net_30", "custom_date"],
        "category": "billing",
        "sort_order": 101,
    },
    {
        "key": "default_billing_mode",
        "label": "Default invoice billing mode",
        "description": "When the invoice builder opens a blank invoice, this is the default tab selection.",
        "value_type": "string",
        "tenant_editable": True,
        "allows_user_override": False,
        "allowed_values": ["line_item", "progress"],
        "category": "billing",
        "sort_order": 102,
    },
]

# platform_setting (null-tenant defaults) — 42 rows, value is JSONB
# has server defaults on created_at/updated_at; unique on (key, tenant_id)
PLATFORM_SETTING_DEFAULTS = [
    {"key": "background_sync_battery_floor_pct", "value": 20},
    {"key": "background_sync_enabled", "value": True},
    {"key": "background_sync_push_interval_minutes", "value": 5},
    {"key": "background_sync_wifi_only", "value": False},
    {"key": "calendar_conflict_auto_expire_days", "value": 60},
    {"key": "calendar_conflict_auto_expire_enabled", "value": True},
    {"key": "calendar_conflict_pre_warning_days", "value": 14},
    {"key": "default_billable_labor_rate_cents", "value": 15000},
    {"key": "default_invoice_terms_days", "value": 0},
    {"key": "default_labor_rate_cents", "value": 8500},
    {"key": "default_quote_validity_days", "value": 30},
    {"key": "default_trial_length_days", "value": 14},
    {"key": "etc_variance_note_required_pct", "value": 10},
    {"key": "etc_variance_owner_notify_pct", "value": 50},
    {"key": "gps_variance_alert_threshold_meters", "value": 500},
    {"key": "loto_confirmation_required", "value": False},
    {"key": "margin_bucket_boundaries", "value": [10, 20, 30]},
    {"key": "margin_target_pct", "value": 20},
    {"key": "max_discount_pct_owner", "value": 15},
    {"key": "offline_hard_limit_hours", "value": 72},
    {"key": "photo_local_retention_days", "value": 7},
    {"key": "photo_upload_wifi_only", "value": True},
    {"key": "qb_auto_expire_customer_direction", "value": None},
    {"key": "qb_auto_expire_customer_enabled", "value": False},
    {"key": "qb_auto_expire_days", "value": 60},
    {"key": "qb_auto_expire_expense_direction", "value": None},
    {"key": "qb_auto_expire_expense_enabled", "value": False},
    {"key": "qb_auto_expire_invoice_direction", "value": None},
    {"key": "qb_auto_expire_invoice_enabled", "value": False},
    {"key": "qb_auto_expire_quote_direction", "value": None},
    {"key": "qb_auto_expire_quote_enabled", "value": False},
    {"key": "qb_pre_warning_days", "value": 14},
    {"key": "report_chart_threshold", "value": 8},
    {"key": "require_approval_for_tech_quotes", "value": True},
    {"key": "sms_quota_cap_policy", "value": "soft"},
    {"key": "tech_color_palette", "value": None},
    {"key": "tenant_mfa_grace_period_days", "value": 7},
    {"key": "tenant_mfa_required", "value": False},
    {"key": "tenant_sync_indicator_pending_amber_threshold", "value": 5},
    {"key": "voice_offline_audio_storage_limit_mb", "value": 500},
    {"key": "voice_persona_tone", "value": "balanced"},
    {"key": "voice_persona_tone_user_override_allowed", "value": True},
    # SD-06B: Invoice reminder schedule defaults
    {"key": "invoice_reminder_days_1", "value": 1},
    {"key": "invoice_reminder_days_2", "value": 7},
    {"key": "invoice_reminder_days_3", "value": 14},
    # SEED-FIX-1: B20 invoice-builder defaults (migration f7f30492c3e4 ownership
    # transferred to seed_core.py — post-schema-restore recovery path).
    {"key": "square_integration_enabled", "value": False},
    {"key": "default_payment_terms", "value": "due_on_receipt"},
    {"key": "default_billing_mode", "value": "line_item"},
]

# ─────────────────────────────────────────────────────────────────────────────


def _load_email_templates() -> list:
    """Load email template JSON files from data/email_templates/."""
    templates = []
    if not EMAIL_TEMPLATES_DIR.exists():
        print(f"  ⚠️  [email_template] Data directory not found: {EMAIL_TEMPLATES_DIR}")
        return templates
    for json_file in sorted(EMAIL_TEMPLATES_DIR.glob("*.json")):
        with open(json_file) as f:
            templates.append(json.load(f))
    return templates


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_core.py — Group A lookup table seeder"
    )
    parser.add_argument(
        "--mode",
        choices=["seed", "inspect", "show"],
        default="seed",
        help="seed: run INSERTs | inspect: show DB state | show: print seed definitions",
    )
    add_env_args(parser)
    return parser.parse_args()


# Cache of tables that have a UUID 'id' column (avoids repeated information_schema queries).
# Populated lazily on first use by _table_has_id_column().
_id_column_cache: set[str] = set()
_no_id_column_cache: set[str] = set()


def _table_has_id_column(db, table: str) -> bool:
    """Check if a table has a column named 'id' (UUID PK without a DB default).

    Many lookup tables use 'code' as the PK and have no 'id' column at all.
    Others use a UUID 'id' PK with no server-side gen_random_uuid() default.
    This check determines whether the INSERT must explicitly provide gen_random_uuid().
    """
    if table in _id_column_cache:
        return True
    if table in _no_id_column_cache:
        return False
    result = db.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = 'id'"
        ),
        {"t": table},
    ).first()
    if result:
        _id_column_cache.add(table)
        return True
    _no_id_column_cache.add(table)
    return False


def _upsert_simple(db, table: str, pk: str, cols: list, rows: list):
    """Insert rows into a table with no tenant_id using ON CONFLICT DO NOTHING.
    Always includes created_at/updated_at=NOW() for StandardAuditMixin tables.
    If the table has a UUID 'id' PK with no DB default, includes gen_random_uuid()."""
    has_id = _table_has_id_column(db, table)
    for row in rows:
        result = db.execute(
            text(f"SELECT 1 FROM public.{table} WHERE {pk} = :{pk}"),
            {pk: row[pk]},
        ).first()
        if result:
            print(f"  ℹ️  [{table}] '{row[pk]}' already exists")
        else:
            if has_id:
                all_cols = ["id", *cols, "created_at", "updated_at"]
                val_str = (
                    "gen_random_uuid(), "
                    + ", ".join(f":{c}" for c in cols)
                    + ", NOW(), NOW()"
                )
            else:
                all_cols = [*cols, "created_at", "updated_at"]
                val_str = ", ".join(f":{c}" for c in cols) + ", NOW(), NOW()"
            col_str = ", ".join(all_cols)
            db.execute(
                text(
                    f"INSERT INTO public.{table} ({col_str}) VALUES ({val_str}) ON CONFLICT DO NOTHING"
                ),
                row,
            )
            print(f"  ✅ [{table}] Inserted '{row[pk]}'")


def _upsert_with_tenant(db, table: str, pk: str, cols: list, rows: list):
    """Insert global rows (tenant_id IS NULL) using ON CONFLICT DO NOTHING.
    Always includes created_at/updated_at=NOW() for StandardAuditMixin tables.
    If the table has a UUID 'id' PK with no DB default, includes gen_random_uuid()."""
    has_id = _table_has_id_column(db, table)
    for row in rows:
        result = db.execute(
            text(
                f"SELECT 1 FROM public.{table} WHERE {pk} = :{pk} AND tenant_id IS NULL"
            ),
            {pk: row[pk]},
        ).first()
        if result:
            print(f"  ℹ️  [{table}] '{row[pk]}' already exists")
        else:
            if has_id:
                all_cols = ["id", *cols, "tenant_id", "created_at", "updated_at"]
                val_str = (
                    "gen_random_uuid(), "
                    + ", ".join(f":{c}" for c in cols)
                    + ", NULL, NOW(), NOW()"
                )
            else:
                all_cols = [*cols, "tenant_id", "created_at", "updated_at"]
                val_str = ", ".join(f":{c}" for c in cols) + ", NULL, NOW(), NOW()"
            col_str = ", ".join(all_cols)
            db.execute(
                text(
                    f"INSERT INTO public.{table} ({col_str}) VALUES ({val_str}) ON CONFLICT DO NOTHING"
                ),
                row,
            )
            print(f"  ✅ [{table}] Inserted '{row[pk]}'")


def mode_seed():
    """Run all Group A seed inserts."""
    print("=== seed_core: seed mode ===\n")

    with get_db_session() as db:
        # Simple tables (no tenant_id)
        for table, defn in SIMPLE_CODE_TABLES.items():
            _upsert_simple(db, table, "code", defn["cols"], defn["rows"])

        # notification_channel: no tenant_id (simple table)
        _upsert_simple(
            db,
            "notification_channel",
            "code",
            NOTIFICATION_CHANNEL_DEF["cols"],
            NOTIFICATION_CHANNEL_DEF["rows"],
        )

        # Tables with tenant_id = NULL for global rows
        for table, defn in TENANT_NULLABLE_CODE_TABLES.items():
            _upsert_with_tenant(db, table, "code", defn["cols"], defn["rows"])

        # entity_type (no tenant_id, code PK)
        for row in ENTITY_TYPE_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.entity_type WHERE code = :code"),
                {"code": row["code"]},
            ).first()
            if result:
                print(f"  ℹ️  [entity_type] '{row['code']}' already exists")
            else:
                db.execute(
                    text(
                        "INSERT INTO public.entity_type (code, name, is_active, created_at, updated_at) VALUES (:code, :name, true, NOW(), NOW()) ON CONFLICT DO NOTHING"
                    ),
                    row,
                )
                print(f"  ✅ [entity_type] Inserted '{row['code']}'")

        # platform_role (no tenant_id, code PK)
        for row in PLATFORM_ROLE_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.platform_role WHERE code = :code"),
                {"code": row["code"]},
            ).first()
            if result:
                print(f"  ℹ️  [platform_role] '{row['code']}' already exists")
            else:
                db.execute(
                    text(
                        "INSERT INTO public.platform_role (code, name, is_active, created_at, updated_at) VALUES (:code, :name, true, NOW(), NOW()) ON CONFLICT DO NOTHING"
                    ),
                    row,
                )
                print(f"  ✅ [platform_role] Inserted '{row['code']}'")

        # job_expense_category (no tenant_id, code PK)
        for row in JOB_EXPENSE_CATEGORY_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.job_expense_category WHERE code = :code"),
                {"code": row["code"]},
            ).first()
            if result:
                print(f"  ℹ️  [job_expense_category] '{row['code']}' already exists")
            else:
                db.execute(
                    text(
                        "INSERT INTO public.job_expense_category (code, name, is_active, created_at, updated_at) VALUES (:code, :name, :is_active, NOW(), NOW()) ON CONFLICT DO NOTHING"
                    ),
                    row,
                )
                print(f"  ✅ [job_expense_category] Inserted '{row['code']}'")

        # qpl_contact_action_type
        for row in QPL_CONTACT_ACTION_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.qpl_contact_action_type WHERE code = :code"),
                {"code": row["code"]},
            ).first()
            if result:
                print(f"  ℹ️  [qpl_contact_action_type] '{row['code']}' already exists")
            else:
                db.execute(
                    text(
                        "INSERT INTO public.qpl_contact_action_type (id, code, name, is_active, created_at, updated_at) VALUES (gen_random_uuid(), :code, :name, true, NOW(), NOW()) ON CONFLICT DO NOTHING"
                    ),
                    row,
                )
                print(f"  ✅ [qpl_contact_action_type] Inserted '{row['code']}'")

        # qco_line_type — global line type rows (tenant_id IS NULL)
        # Seeded by Alembic migration 9f8116bb6ad1 but needed explicitly for fresh E2E DBs
        _qco_line_type_rows = [
            {"code": "labor", "name": "Labor", "is_default": True, "is_active": True},
            {
                "code": "material",
                "name": "Material",
                "is_default": False,
                "is_active": True,
            },
            {"code": "misc", "name": "Misc", "is_default": False, "is_active": True},
            {
                "code": "discount",
                "name": "Discount",
                "is_default": False,
                "is_active": True,
            },
            # SD-2: note added
            {"code": "note", "name": "Note", "is_default": False, "is_active": True},
        ]
        for row in _qco_line_type_rows:
            result = db.execute(
                text(
                    "SELECT id FROM public.qco_line_type WHERE code = :code AND tenant_id IS NULL LIMIT 1"
                ),
                {"code": row["code"]},
            ).first()
            if result:
                print(f"  ℹ️  [qco_line_type] '{row['code']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.qco_line_type
                            (id, tenant_id, code, name, is_default, is_active, created_at, updated_at)
                        VALUES
                            (gen_random_uuid(), NULL, :code, :name, :is_default, :is_active, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    row,
                )
                print(f"  ✅ [qco_line_type] Inserted '{row['code']}'")

        # customer_comm_template_type — seeded here (was only in migrations; needed for fresh E2E DB)
        # Schema: code, slug, name, description, category, preferred_channel, initiator,
        #         requires_approval, send_mode, trigger_event, is_system, is_active, sort_order,
        #         created_at, updated_at (id has gen_random_uuid() default added by init_e2e_schema)
        _cust_comm_template_type_rows = [
            {
                "code": "on_my_way",
                "slug": "on_my_way",
                "name": "On My Way",
                "category": "during_job",
                "preferred_channel": "sms",
                "initiator": "tech",
                "requires_approval": False,
                "send_mode": "manual",
                "is_system": True,
                "is_active": True,
                "sort_order": 10,
            },
            {
                "code": "running_late",
                "slug": "running_late",
                "name": "Running Late",
                "category": "during_job",
                "preferred_channel": "sms",
                "initiator": "tech",
                "requires_approval": False,
                "send_mode": "manual",
                "is_system": True,
                "is_active": True,
                "sort_order": 20,
            },
            {
                "code": "arrived",
                "slug": "arrived",
                "name": "Arrived",
                "category": "during_job",
                "preferred_channel": "sms",
                "initiator": "tech",
                "requires_approval": False,
                "send_mode": "manual",
                "is_system": True,
                "is_active": True,
                "sort_order": 30,
            },
            {
                "code": "parts_delay",
                "slug": "parts_delay",
                "name": "Parts Delay",
                "category": "during_job",
                "preferred_channel": "sms",
                "initiator": "tech",
                "requires_approval": False,
                "send_mode": "manual",
                "is_system": True,
                "is_active": True,
                "sort_order": 40,
            },
            {
                "code": "change_order_approval",
                "slug": "change_order_approval",
                "name": "Change Order Approval",
                "category": "during_job",
                "preferred_channel": "sms",
                "initiator": "owner",
                "requires_approval": True,
                "send_mode": "manual",
                "is_system": True,
                "is_active": True,
                "sort_order": 50,
            },
            {
                "code": "job_complete",
                "slug": "job_complete",
                "name": "Job Complete",
                "category": "post_job",
                "preferred_channel": "sms",
                "initiator": "tech",
                "requires_approval": False,
                "send_mode": "manual",
                "is_system": True,
                "is_active": True,
                "sort_order": 60,
            },
            {
                "code": "invoice_sent",
                "slug": "invoice_sent",
                "name": "Invoice Sent",
                "category": "post_job",
                "preferred_channel": "email",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": True,
                "sort_order": 70,
            },
            {
                "code": "payment_reminder",
                "slug": "payment_reminder",
                "name": "Payment Reminder",
                "category": "post_job",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": True,
                "sort_order": 80,
            },
            {
                "code": "payment_received",
                "slug": "payment_received",
                "name": "Payment Received",
                "category": "post_job",
                "preferred_channel": "email",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": True,
                "sort_order": 90,
            },
            {
                "code": "confirm_appointment",
                "slug": "confirm_appointment",
                "name": "Confirm Appointment",
                "category": "pre_appointment",
                "preferred_channel": "sms",
                "initiator": "tech",
                "requires_approval": False,
                "send_mode": "manual",
                "is_system": True,
                "is_active": True,
                "sort_order": 100,
            },
            {
                "code": "tech_assigned",
                "slug": "tech_assigned",
                "name": "Tech Assigned",
                "category": "pre_appointment",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": True,
                "sort_order": 110,
            },
            {
                "code": "quote_accepted",
                "slug": "quote_accepted",
                "name": "Quote Accepted",
                "category": "quoting",
                "preferred_channel": "email",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": True,
                "sort_order": 120,
            },
            {
                "code": "quote_expiring",
                "slug": "quote_expiring",
                "name": "Quote Expiring",
                "category": "quoting",
                "preferred_channel": "email",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": True,
                "sort_order": 130,
            },
            {
                "code": "appointment_reminder_24h",
                "slug": "appointment_reminder_24h",
                "name": "Appointment Reminder 24h",
                "category": "pre_appointment",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 200,
            },
            {
                "code": "appointment_reminder_1h",
                "slug": "appointment_reminder_1h",
                "name": "Appointment Reminder 1h",
                "category": "pre_appointment",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 210,
            },
            {
                "code": "quote_follow_up",
                "slug": "quote_follow_up",
                "name": "Quote Follow Up",
                "category": "quoting",
                "preferred_channel": "email",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 220,
            },
            {
                "code": "quote_revised",
                "slug": "quote_revised",
                "name": "Quote Revised",
                "category": "quoting",
                "preferred_channel": "email",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 230,
            },
            {
                "code": "payment_overdue",
                "slug": "payment_overdue",
                "name": "Payment Overdue",
                "category": "post_job",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 240,
            },
            {
                "code": "receipt",
                "slug": "receipt",
                "name": "Receipt",
                "category": "post_job",
                "preferred_channel": "email",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 250,
            },
            {
                "code": "warranty_info",
                "slug": "warranty_info",
                "name": "Warranty Info",
                "category": "post_job",
                "preferred_channel": "email",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 260,
            },
            {
                "code": "review_request",
                "slug": "review_request",
                "name": "Review Request",
                "category": "relationship",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 270,
            },
            {
                "code": "referral_request",
                "slug": "referral_request",
                "name": "Referral Request",
                "category": "relationship",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 280,
            },
            {
                "code": "annual_safety_check",
                "slug": "annual_safety_check",
                "name": "Annual Safety Check",
                "category": "relationship",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 290,
            },
            {
                "code": "service_anniversary",
                "slug": "service_anniversary",
                "name": "Service Anniversary",
                "category": "relationship",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 300,
            },
            {
                "code": "customer_cancellation_confirmed",
                "slug": "customer_cancellation_confirmed",
                "name": "Customer Cancellation Confirmed",
                "category": "exception",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 310,
            },
            {
                "code": "tech_cancellation",
                "slug": "tech_cancellation",
                "name": "Tech Cancellation",
                "category": "exception",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 320,
            },
            {
                "code": "no_show",
                "slug": "no_show",
                "name": "No Show",
                "category": "exception",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": False,
                "sort_order": 330,
            },
            {
                "code": "recurring_job_scheduled",
                "slug": "recurring_job_scheduled",
                "name": "Recurring Job Scheduled",
                "category": "pre_appointment",
                "preferred_channel": "sms",
                "initiator": "system",
                "requires_approval": False,
                "send_mode": "automated",
                "is_system": True,
                "is_active": True,
                "sort_order": 200,
            },
        ]
        for row in _cust_comm_template_type_rows:
            result = db.execute(
                text(
                    "SELECT 1 FROM public.customer_comm_template_type WHERE code = :code"
                ),
                {"code": row["code"]},
            ).first()
            if result:
                print(
                    f"  ℹ️  [customer_comm_template_type] '{row['code']}' already exists"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.customer_comm_template_type
                            (code, slug, name, category, preferred_channel, initiator,
                             requires_approval, send_mode, is_system, is_active, sort_order,
                             created_at, updated_at)
                        VALUES
                            (:code, :slug, :name, :category, :preferred_channel, :initiator,
                             :requires_approval, :send_mode, :is_system, :is_active, :sort_order,
                             NOW(), NOW())
                        ON CONFLICT (code) DO NOTHING
                    """),
                    row,
                )
                print(f"  ✅ [customer_comm_template_type] Inserted '{row['code']}'")

        # NOTE: subscription_status is NOT seeded here (test-fixture-managed).

        # notification_category
        for nc in NOTIFICATION_CATEGORY_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.notification_category WHERE code = :code"),
                {"code": nc["code"]},
            ).first()
            if result:
                print(f"  ℹ️  [notification_category] '{nc['code']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.notification_category (code, display_label, description, display_order)
                        VALUES (:code, :display_label, :description, :display_order)
                        ON CONFLICT DO NOTHING
                    """),
                    nc,
                )
                print(f"  ✅ [notification_category] Inserted '{nc['code']}'")

        # notification_default_policy
        for dp in NOTIFICATION_DEFAULT_POLICY_ROWS:
            result = db.execute(
                text("""
                    SELECT 1 FROM public.notification_default_policy
                    WHERE category_id = :category_id AND channel = :channel AND tenant_id IS NULL
                """),
                dp,
            ).first()
            if result:
                print(
                    f"  ℹ️  [notification_default_policy] {dp['category_id']}/{dp['channel']} already exists"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.notification_default_policy (id, category_id, channel, enabled, tenant_id)
                        VALUES (gen_random_uuid(), :category_id, :channel, :enabled, NULL)
                        ON CONFLICT DO NOTHING
                    """),
                    dp,
                )
                print(
                    f"  ✅ [notification_default_policy] Inserted {dp['category_id']}/{dp['channel']}"
                )

        # ── QB-H1: global app_service row (deterministic UUID, seed ↔ migration parity) ──
        # The category + provider rows are seeded above via SIMPLE_CODE_TABLES.
        # This global app_service row is a pure catalog entry (tenant_id IS NULL,
        # external_account_id NULL) — tenant-scoped connection rows are created by
        # the OAuth flow at runtime, never seeded.
        _global_app_service_id = "00000000-0000-0000-0000-000000000aa5"
        result = db.execute(
            text("SELECT 1 FROM public.app_service WHERE id = :gid"),
            {"gid": _global_app_service_id},
        ).first()
        if result:
            print(
                f"  ℹ️  [app_service] global row '{_global_app_service_id}' already exists"
            )
        else:
            db.execute(
                text(
                    """
                    INSERT INTO public.app_service
                        (id, tenant_id, name, category_code, provider_code,
                         is_active, external_account_id, created_at, updated_at)
                    VALUES
                        (:gid, NULL, 'QuickBooks Online', 'accounting', 'quickbooks',
                         true, NULL, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"gid": _global_app_service_id},
            )
            print(f"  ✅ [app_service] Inserted global row '{_global_app_service_id}'")

        # tax_rate_version (AppendOnly — created_at NOT NULL, no server default, no updated_at)
        for trv in TAX_RATE_VERSION_ROWS:
            result = db.execute(
                text("""
                    SELECT 1 FROM public.tax_rate_version
                    WHERE jurisdiction_code = :jcode AND rate_pct = :rate
                """),
                {"jcode": trv["jurisdiction_code"], "rate": trv["rate_pct"]},
            ).first()
            if result:
                print(
                    f"  ℹ️  [tax_rate_version] '{trv['jurisdiction_code']}' @ {trv['rate_pct']}% already exists"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.tax_rate_version
                        (jurisdiction_code, description, rate_pct, valid_period, recorded_at, created_at, taxability_code)
                        VALUES (:jcode, :description, :rate, CAST(:valid_period AS tstzrange), NOW(), NOW(), 'taxable')
                    """),
                    {
                        "jcode": trv["jurisdiction_code"],
                        "description": trv["description"],
                        "rate": trv["rate_pct"],
                        "valid_period": trv["valid_period"],
                    },
                )
                print(
                    f"  ✅ [tax_rate_version] Inserted '{trv['jurisdiction_code']}' @ {trv['rate_pct']}%"
                )

        # ── SD-01 NEW TABLES ─────────────────────────────────────────────────

        # notification_category_sub_trigger — code PK (text), no tenant_id
        # has server defaults on created_at/updated_at
        for row in NOTIFICATION_CATEGORY_SUB_TRIGGER_ROWS:
            result = db.execute(
                text(
                    "SELECT 1 FROM public.notification_category_sub_trigger WHERE code = :code"
                ),
                {"code": row["code"]},
            ).first()
            if result:
                print(
                    f"  ℹ️  [notification_category_sub_trigger] '{row['code']}' already exists"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.notification_category_sub_trigger
                        (code, category_id, display_label, forced_minimum_push_uniform, forced_minimum_push_recipient_only)
                        VALUES (:code, :category_id, :display_label, :forced_minimum_push_uniform, :forced_minimum_push_recipient_only)
                        ON CONFLICT DO NOTHING
                    """),
                    row,
                )
                print(
                    f"  ✅ [notification_category_sub_trigger] Inserted '{row['code']}'"
                )

        # product_feature — code PK, no tenant_id, StandardAuditMixin (no server defaults)
        # First: remove orphaned rows from renamed/deprecated features (MKT-B11, SD-07, SD-2)
        for orphan_code in PRODUCT_FEATURE_CLEANUP_CODES:
            result = db.execute(
                text("DELETE FROM public.product_feature WHERE code = :code"),
                {"code": orphan_code},
            )
            if result.rowcount:
                print(f"  🗑  [product_feature] Removed orphaned '{orphan_code}'")
        # Then: upsert current feature set
        for row in PRODUCT_FEATURE_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.product_feature WHERE code = :code"),
                {"code": row["code"]},
            ).first()
            if result:
                print(f"  ℹ️  [product_feature] '{row['code']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.product_feature (code, name, unit, description, created_at, updated_at)
                        VALUES (:code, :name, :unit, :description, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    row,
                )
                print(f"  ✅ [product_feature] Inserted '{row['code']}'")

        # jwk_status — AppendOnly (created_at only, NO updated_at), id UUID PK, no tenant_id
        for row in JWK_STATUS_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.jwk_status WHERE code = :code"),
                {"code": row["code"]},
            ).first()
            if result:
                print(f"  ℹ️  [jwk_status] '{row['code']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.jwk_status (id, code, name, is_default, is_signable, created_at)
                        VALUES (gen_random_uuid(), :code, :name, :is_default, :is_signable, NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    row,
                )
                print(f"  ✅ [jwk_status] Inserted '{row['code']}'")

        # tenant_user_role — code PK, no tenant_id, StandardAuditMixin (no server defaults)
        # permissions is JSONB
        for row in TENANT_USER_ROLE_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.tenant_user_role WHERE code = :code"),
                {"code": row["code"]},
            ).first()
            if result:
                # Existing row: keep the permissions field convergent with the
                # seed definition (value-scoped, no-op when already equal;
                # updated_at touched only on change). Only permissions +
                # updated_at may change — never name/description/is_default/
                # is_active (PLP-FIX-7 §C.1).
                permissions_json = json.dumps(row["permissions"])
                update_result = db.execute(
                    text("""
                        UPDATE public.tenant_user_role
                        SET permissions = CAST(:permissions AS jsonb), updated_at = now()
                        WHERE code = :code AND permissions <> CAST(:permissions AS jsonb)
                    """),
                    {"code": row["code"], "permissions": permissions_json},
                )
                if update_result.rowcount:
                    print(
                        f"  🔄 [tenant_user_role] '{row['code']}' permissions "
                        f"converged ({update_result.rowcount} row updated)"
                    )
                else:
                    print(f"  ℹ️  [tenant_user_role] '{row['code']}' already exists")
            else:
                permissions_json = json.dumps(row["permissions"])
                db.execute(
                    text("""
                        INSERT INTO public.tenant_user_role
                        (code, name, description, permissions, is_default, is_active, created_at, updated_at)
                        VALUES (:code, :name, :description, CAST(:permissions AS jsonb),
                                :is_default, :is_active, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "code": row["code"],
                        "name": row["name"],
                        "description": row["description"],
                        "permissions": permissions_json,
                        "is_default": row["is_default"],
                        "is_active": row["is_active"],
                    },
                )
                print(f"  ✅ [tenant_user_role] Inserted '{row['code']}'")

        # sync_conflict_classification_matrix — has server defaults on created_at/updated_at
        # id has gen_random_uuid() default. Unique on (operation_type, trigger_condition, tenant_id IS NULL).
        for row in SYNC_CONFLICT_MATRIX_ROWS:
            result = db.execute(
                text("""
                    SELECT 1 FROM public.sync_conflict_classification_matrix
                    WHERE operation_type = :operation_type AND trigger_condition = :trigger_condition
                    AND tenant_id IS NULL
                """),
                row,
            ).first()
            if result:
                print(
                    f"  ℹ️  [sync_conflict_classification_matrix] '{row['operation_type']}/{row['trigger_condition']}' already exists"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.sync_conflict_classification_matrix
                        (id, operation_type, trigger_condition, severity, classification_reason, is_active, tenant_id)
                        VALUES (gen_random_uuid(), :operation_type, :trigger_condition, :severity,
                                :classification_reason, true, NULL)
                        ON CONFLICT DO NOTHING
                    """),
                    row,
                )
                print(
                    f"  ✅ [sync_conflict_classification_matrix] Inserted '{row['operation_type']}/{row['trigger_condition']}'"
                )

        # communication_template — has id (gen_random_uuid default), tenant_id (nullable),
        # server defaults on created_at/updated_at
        for row in COMMUNICATION_TEMPLATE_ROWS:
            result = db.execute(
                text("""
                    SELECT 1 FROM public.communication_template
                    WHERE template_code = :template_code AND channel = :channel AND tenant_id IS NULL
                """),
                row,
            ).first()
            if result:
                print(
                    f"  ℹ️  [communication_template] '{row['template_code']}/{row['channel']}' already exists"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.communication_template
                        (id, tenant_id, template_code, channel, subject, body_template, is_active)
                        VALUES (gen_random_uuid(), NULL, :template_code, :channel, :subject, :body_template, true)
                        ON CONFLICT DO NOTHING
                    """),
                    row,
                )
                print(
                    f"  ✅ [communication_template] Inserted '{row['template_code']}/{row['channel']}'"
                )

        # email_template — template_id PK (text), StandardAuditMixin (NO server defaults)
        # Loads from JSON files in data/email_templates/
        email_templates = _load_email_templates()
        for tmpl in email_templates:
            result = db.execute(
                text(
                    "SELECT 1 FROM public.email_template WHERE template_id = :template_id"
                ),
                {"template_id": tmpl["template_id"]},
            ).first()
            if result:
                print(f"  ℹ️  [email_template] '{tmpl['template_id']}' already exists")
            else:
                variables_json = json.dumps(tmpl.get("variables", []))
                db.execute(
                    text("""
                        INSERT INTO public.email_template
                        (template_id, display_name, category, subject_template, body_html_template,
                         body_plain_template, variables, is_active, created_at, updated_at)
                        VALUES (:template_id, :display_name, :category, :subject_template,
                                :body_html_template, :body_plain_template,
                                CAST(:variables AS jsonb), true, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "template_id": tmpl["template_id"],
                        "display_name": tmpl["display_name"],
                        "category": tmpl["category"],
                        "subject_template": tmpl["subject_template"],
                        "body_html_template": tmpl["body_html_template"],
                        "body_plain_template": tmpl["body_plain_template"],
                        "variables": variables_json,
                    },
                )
                print(f"  ✅ [email_template] Inserted '{tmpl['template_id']}'")

        # platform_setting_catalog — key PK, has server defaults on created_at/updated_at
        # SEED-FIX-1: B20 keys include optional description + allowed_values (jsonb).
        for row in PLATFORM_SETTING_CATALOG_ROWS:
            result = db.execute(
                text("SELECT 1 FROM public.platform_setting_catalog WHERE key = :key"),
                {"key": row["key"]},
            ).first()
            if result:
                print(f"  ℹ️  [platform_setting_catalog] '{row['key']}' already exists")
            else:
                # Build INSERT dynamically — description and allowed_values are optional.
                insert_cols = [
                    "key",
                    "label",
                    "value_type",
                    "tenant_editable",
                    "allows_user_override",
                    "category",
                    "sort_order",
                ]
                insert_params = {col: row[col] for col in insert_cols}
                col_list = ", ".join(insert_cols)
                param_list = ", ".join(f":{col}" for col in insert_cols)

                if "description" in row:
                    insert_cols.append("description")
                    insert_params["description"] = row["description"]
                    col_list = ", ".join(insert_cols)
                    param_list = ", ".join(f":{col}" for col in insert_cols)

                if "allowed_values" in row:
                    insert_cols.append("allowed_values")
                    allowed_json = (
                        json.dumps(row["allowed_values"])
                        if row["allowed_values"] is not None
                        else None
                    )
                    insert_params["allowed_values"] = allowed_json
                    col_list = ", ".join(insert_cols)
                    # Use CAST for jsonb column; plain :param for others
                    param_list = ", ".join(
                        f"CAST(:{col} AS jsonb)"
                        if col == "allowed_values"
                        else f":{col}"
                        for col in insert_cols
                    )

                db.execute(
                    text(
                        f"INSERT INTO public.platform_setting_catalog "
                        f"({col_list}) VALUES ({param_list}) "
                        f"ON CONFLICT DO NOTHING"
                    ),
                    insert_params,
                )
                print(f"  ✅ [platform_setting_catalog] Inserted '{row['key']}'")

        # platform_setting (null-tenant defaults) — key+tenant_id unique
        # has server defaults on created_at/updated_at; value is JSONB (None → SQL NULL)
        for row in PLATFORM_SETTING_DEFAULTS:
            result = db.execute(
                text("""
                    SELECT 1 FROM public.platform_setting
                    WHERE key = :key AND tenant_id IS NULL
                """),
                {"key": row["key"]},
            ).first()
            if result:
                print(
                    f"  ℹ️  [platform_setting] '{row['key']}' (null-tenant) already exists"
                )
            else:
                value_json = json.dumps(row["value"])
                db.execute(
                    text("""
                        INSERT INTO public.platform_setting (key, value, tenant_id)
                        VALUES (:key, CAST(:value AS jsonb), NULL)
                        ON CONFLICT DO NOTHING
                    """),
                    {"key": row["key"], "value": value_json},
                )
                print(
                    f"  ✅ [platform_setting] Inserted '{row['key']}' (null-tenant default)"
                )

        # SD-09: quote_template — 3 Alembic-owned system templates (tenant_id IS NULL)
        # INSERT ON CONFLICT (id) DO NOTHING to preserve Alembic ownership.
        # UUIDs confirmed from live DB 2026-07-06.
        quote_templates = [
            {
                "id": "608e2c6e-344c-4a6d-9d43-bd86960d202f",
                "name": "Service Call Basic",
                "style": "component",
                "category": "service_call",
            },
            {
                "id": "7d1647ca-aac4-4be1-bdb2-74325f37198a",
                "name": "Installation Standard",
                "style": "deliverable",
                "category": "installation",
            },
            {
                "id": "d615ecdf-fb53-453c-9631-e895effa1bf5",
                "name": "Fixed Bid Simple",
                "style": "lump_sum",
                "category": None,
            },
        ]
        for qt in quote_templates:
            result = db.execute(
                text(
                    "SELECT 1 FROM public.quote_template WHERE id = CAST(:id AS uuid)"
                ),
                {"id": qt["id"]},
            ).first()
            if result:
                print(f"  ℹ️  [quote_template] '{qt['name']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.quote_template
                        (id, tenant_id, name, style, category, current_version,
                         is_active, is_system_template, created_at, updated_at)
                        VALUES (CAST(:id AS uuid), NULL, :name, :style, :category, 1,
                                true, true, NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                    """),
                    qt,
                )
                print(f"  ✅ [quote_template] Inserted '{qt['name']}'")

        # SD-7 Batch 1: quote_template_line — 2–4 lines per system template.
        # Post QT-FIX-1: system-template lines are tenant_id = NULL (platform-level),
        # matching the already-nullable parent quote_template.tenant_id. No test-tenant
        # dependency — seed_core.py can run before or after seed_test_tenant.py.
        # Look up qco_line_type IDs (stable Alembic-managed rows)
        qco_types = {
            row.code: str(row.id)
            for row in db.execute(
                text(
                    "SELECT id, code FROM public.qco_line_type WHERE tenant_id IS NULL"
                )
            ).fetchall()
        }
        qco_labor = qco_types.get("labor")
        qco_material = qco_types.get("material")
        qco_misc = qco_types.get("misc")

        # Template line definitions: (template_id, display_order, qco_type, description,
        #                              default_quantity, default_unit_price_cents)
        template_lines = [
            # ── Service Call Basic (608e2c6e-...) ─────────────────────────
            # 3 lines: labor service call + material (breaker) + misc permit
            (
                "608e2c6e-344c-4a6d-9d43-bd86960d202f",
                1,
                qco_labor,
                "Service call labor — diagnostic and repair",
                1,
                15000,
            ),
            (
                "608e2c6e-344c-4a6d-9d43-bd86960d202f",
                2,
                qco_material,
                "Replacement parts / materials",
                1,
                5000,
            ),
            (
                "608e2c6e-344c-4a6d-9d43-bd86960d202f",
                3,
                qco_misc,
                "Trip charge / travel fee",
                1,
                7500,
            ),
            # ── Installation Standard (7d1647ca-...) ───────────────────────
            # 4 lines: labor + material + material + permit
            (
                "7d1647ca-aac4-4be1-bdb2-74325f37198a",
                1,
                qco_labor,
                "Installation labor — rough-in and finish",
                1,
                45000,
            ),
            (
                "7d1647ca-aac4-4be1-bdb2-74325f37198a",
                2,
                qco_material,
                "Primary materials and components",
                1,
                20000,
            ),
            (
                "7d1647ca-aac4-4be1-bdb2-74325f37198a",
                3,
                qco_material,
                "Conduit and wiring",
                1,
                8000,
            ),
            (
                "7d1647ca-aac4-4be1-bdb2-74325f37198a",
                4,
                qco_misc,
                "Permit and inspection fees",
                1,
                25000,
            ),
            # ── Fixed Bid Simple (d615ecdf-...) ────────────────────────────
            # 2 lines: lump-sum labor + lump-sum materials
            (
                "d615ecdf-fb53-453c-9631-e895effa1bf5",
                1,
                qco_labor,
                "Labor — all work as described in scope",
                1,
                80000,
            ),
            (
                "d615ecdf-fb53-453c-9631-e895effa1bf5",
                2,
                qco_material,
                "Materials — all parts and supplies included",
                1,
                40000,
            ),
        ]

        for (
            tmpl_id,
            display_order,
            qco_type_id,
            description,
            qty,
            price,
        ) in template_lines:
            if not qco_type_id:
                print("  ⚠️  [quote_template_line] qco_type not found — skipping line")
                continue
            # Check if template line already exists for this template+order
            # (tenant_id IS NULL — system-template lines are platform-level)
            exists = db.execute(
                text("""
                    SELECT 1 FROM public.quote_template_line
                    WHERE quote_template_id = CAST(:tmpl_id AS uuid)
                      AND tenant_id IS NULL
                      AND display_order = :display_order
                """),
                {
                    "tmpl_id": tmpl_id,
                    "display_order": display_order,
                },
            ).first()
            if exists:
                print(
                    f"  ℹ️  [quote_template_line] template={tmpl_id[:8]}… "
                    f"order={display_order} already exists"
                )
                continue

            db.execute(
                text("""
                    INSERT INTO public.quote_template_line
                    (id, tenant_id, quote_template_id, display_order,
                     qco_line_type_id, description, default_quantity,
                     default_unit_price_cents, customer_visible,
                     is_section_header, is_active, created_at, updated_at)
                    VALUES (
                        gen_random_uuid(),
                        NULL,
                        CAST(:tmpl_id AS uuid),
                        :display_order,
                        CAST(:qco_type_id AS uuid),
                        :description,
                        :qty,
                        :price,
                        true, false, true,
                        NOW(), NOW()
                    )
                """),
                {
                    "tmpl_id": tmpl_id,
                    "display_order": display_order,
                    "qco_type_id": qco_type_id,
                    "description": description,
                    "qty": qty,
                    "price": price,
                },
            )
            print(
                f"  ✅ [quote_template_line] template={tmpl_id[:8]}… "
                f"order={display_order} '{description[:40]}'"
            )

        # Count system-template lines (tenant_id IS NULL) across the 3
        # system templates for a sanity-check log line.
        count_result = db.execute(
            text("""
                SELECT COUNT(*) FROM public.quote_template_line qtl
                JOIN public.quote_template qt ON qtl.quote_template_id = qt.id
                WHERE qt.tenant_id IS NULL AND qtl.tenant_id IS NULL
            """)
        ).scalar()
        print(
            f"  ✅ [quote_template_line] System template lines seeded "
            f"(3 templates: 3 + 4 + 2 = 9 lines; {count_result} NULL-tenant lines present)"
        )

        db.commit()

        # CLASS-B1: job_type platform defaults (tenant_id = NULL)
        # Identical to migration seed rows — this is the schema-restore recovery path.
        job_type_rows = [
            ("service_call", "Service Call", 10),
            ("troubleshoot", "Troubleshoot / Diagnostic", 20),
            ("panel_upgrade", "Panel Upgrade", 30),
            ("rewire", "Rewire", 40),
            ("lighting", "Lighting", 50),
            ("generator_install", "Generator Install", 60),
            ("ev_charger_install", "EV Charger Install", 70),
            ("new_construction", "New Construction", 80),
            ("inspection", "Inspection", 90),
            ("warranty", "Warranty", 100),
            ("other", "Other", 999),
        ]
        with get_db_session() as db:
            for code, label, sort_order in job_type_rows:
                exists = db.execute(
                    text(
                        "SELECT 1 FROM public.job_type WHERE code = :code AND tenant_id IS NULL"
                    ),
                    {"code": code},
                ).first()
                if exists:
                    print(f"  ℹ️  [job_type] '{code}' already exists")
                    continue
                db.execute(
                    text(
                        """
                        INSERT INTO public.job_type
                            (id, tenant_id, code, label, sort_order, is_active, created_at, updated_at)
                        VALUES
                            (gen_random_uuid(), NULL, :code, :label, :sort_order, true, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"code": code, "label": label, "sort_order": sort_order},
                )
                print(f"  ✅ [job_type] Inserted '{code}' ({label})")
            db.commit()
        print("  ✅ [job_type] 11 platform-default rows present")

    print("\n🎉 seed_core complete — all Group A lookup data present.")


def mode_inspect():
    """Show current row data for all Group A tables."""
    print("=== seed_core: inspect mode ===\n")

    all_tables = [
        # (table_name, select_cols, has_tenant_id)
        ("address_type", "code, name, is_default, is_active", True),
        ("contact_type", "code, name, is_default, is_active", True),
        ("taxability_code", "code, name, is_active", False),
        ("currency", "code, name, symbol, is_active", False),
        ("job_status", "code, name, is_default, is_terminal, is_active", True),
        ("quote_status", "code, name, is_default, is_terminal, is_active", True),
        ("invoice_status", "code, name, is_default, is_terminal, is_active", True),
        ("payment_status", "code, name, is_default, is_terminal, is_active", True),
        ("payment_type", "code, name, is_active", True),
        ("entity_type", "code, name, is_active", False),
        ("platform_role", "code, name, is_active", False),
        ("tenant_user_status", "code, name, is_default, is_active", True),
        ("customer_lifecycle_status", "code, name, is_default, is_active", True),
        ("site_lifecycle_status", "code, name, is_default, is_active", True),
        ("supplier_lifecycle_status", "code, name, is_default, is_active", True),
        ("notification_channel", "code, name, is_active", False),
        ("notification_type", "code, name, is_active", True),
        ("subscription_status", "code, name, is_billing_active", False),
        ("app_service_category", "code, description, is_active", False),
        ("app_service_provider", "code, description, is_active", False),
        ("quote_link_status", "code, name, is_default, is_active", True),
        ("supplier_item_category", "code, name, is_active", True),
        ("supplier_item_uom", "code, name, is_default, is_active", True),
        ("webhook_event_type", "code, name, is_active", False),
        ("sso_provider", "code, name, is_active", False),
        # CLASS-B1: job_type platform defaults (shown as tenant_id IS NULL rows)
        ("job_type", "code, label, sort_order, is_active", True),
    ]

    # tax_rate_version — AppendOnly, no tenant_id; display separately
    tax_rate_inspect_query = """
        SELECT jurisdiction_code, description, rate_pct, valid_period::text
        FROM public.tax_rate_version
        ORDER BY jurisdiction_code
    """

    with get_db_session() as db:
        for table, cols, has_tenant in all_tables:
            try:
                where = "WHERE tenant_id IS NULL " if has_tenant else ""
                rows = db.execute(
                    text(f"SELECT {cols} FROM public.{table} {where}ORDER BY code")
                ).fetchall()
                print(f"  [{table}]  {len(rows)} row(s)")
                for r in rows:
                    vals = "  ".join(f"{k}={v}" for k, v in r._mapping.items())
                    print(f"    • {vals}")
            except Exception as e:
                print(f"  [{table}]  ERROR: {e}")
                db.rollback()
            print()

        # job_expense_category (no tenant_id)
        try:
            rows = db.execute(
                text(
                    "SELECT code, is_active FROM public.job_expense_category ORDER BY code"
                )
            ).fetchall()
            print(f"  [job_expense_category]  {len(rows)} row(s)")
            for r in rows:
                print(f"    • code={r.code}  is_active={r.is_active}")
        except Exception as e:
            print(f"  [job_expense_category]  ERROR: {e}")
        print()

        # QB-H1: app_service global row (UUID PK, tenant_id IS NULL — not in the
        # code-ordered loop above which assumes an ORDER BY code column)
        try:
            rows = db.execute(
                text(
                    """
                    SELECT id, name, category_code, provider_code, is_active
                    FROM public.app_service
                    WHERE tenant_id IS NULL
                    ORDER BY provider_code
                    """
                )
            ).fetchall()
            print(f"  [app_service]  {len(rows)} global row(s)")
            for r in rows:
                print(
                    f"    • id={r.id}  name='{r.name}'  "
                    f"category={r.category_code}  provider={r.provider_code}  "
                    f"is_active={r.is_active}"
                )
        except Exception as e:
            print(f"  [app_service]  ERROR: {e}")
        print()

        # qpl_contact_action_type
        try:
            rows = db.execute(
                text(
                    "SELECT code, name, is_active FROM public.qpl_contact_action_type ORDER BY code"
                )
            ).fetchall()
            print(f"  [qpl_contact_action_type]  {len(rows)} row(s)")
            for r in rows:
                print(f"    • {r.code}  '{r.name}'  is_active={r.is_active}")
        except Exception as e:
            print(f"  [qpl_contact_action_type]  ERROR: {e}")
        print()

        # notification_category
        try:
            rows = db.execute(
                text(
                    "SELECT code, display_label, description, display_order FROM public.notification_category ORDER BY display_order"
                )
            ).fetchall()
            print(f"  [notification_category]  {len(rows)} row(s)")
            for r in rows:
                desc = (
                    (r.description[:58] + "…")
                    if r.description and len(r.description) > 58
                    else (r.description or "")
                )
                print(f"    • [{r.display_order}] {r.code:<32}  '{r.display_label}'")
                print(f"          {desc}")
        except Exception as e:
            print(f"  [notification_category]  ERROR: {e}")
        print()

        # notification_default_policy
        try:
            rows = db.execute(
                text("""
                    SELECT category_id, channel, enabled
                    FROM public.notification_default_policy
                    WHERE tenant_id IS NULL
                    ORDER BY category_id, channel
                """)
            ).fetchall()
            print(f"  [notification_default_policy]  {len(rows)} row(s)")
            for r in rows:
                print(
                    f"    • {r.category_id:<30} channel={r.channel:<8}  enabled={r.enabled}"
                )
        except Exception as e:
            print(f"  [notification_default_policy]  ERROR: {e}")

        # tax_rate_version (AppendOnly, no tenant_id)
        try:
            rows = db.execute(text(tax_rate_inspect_query)).fetchall()
            print(f"\n  [tax_rate_version]  {len(rows)} row(s)")
            for r in rows:
                print(
                    f"    • {r.jurisdiction_code:<20} rate={r.rate_pct}%  period={r.valid_period}  '{r.description}'"
                )
        except Exception as e:
            print(f"  [tax_rate_version]  ERROR: {e}")
        print()

        # ── SD-01 new tables ─────────────────────────────────────────────────

        try:
            rows = db.execute(
                text(
                    "SELECT code, category_id, display_label FROM public.notification_category_sub_trigger ORDER BY code"
                )
            ).fetchall()
            print(f"  [notification_category_sub_trigger]  {len(rows)} row(s)")
            for r in rows:
                print(f"    • {r.code:<50}  category={r.category_id}")
        except Exception as e:
            print(f"  [notification_category_sub_trigger]  ERROR: {e}")
        print()

        try:
            rows = db.execute(
                text(
                    "SELECT code, name, unit FROM public.product_feature ORDER BY code"
                )
            ).fetchall()
            print(f"  [product_feature]  {len(rows)} row(s)")
            for r in rows:
                print(f"    • {r.code}  '{r.name}'  unit={r.unit}")
        except Exception as e:
            print(f"  [product_feature]  ERROR: {e}")
        print()

        try:
            rows = db.execute(
                text(
                    "SELECT code, name, is_default, is_signable FROM public.jwk_status ORDER BY code"
                )
            ).fetchall()
            print(f"  [jwk_status]  {len(rows)} row(s)")
            for r in rows:
                print(
                    f"    • {r.code}  '{r.name}'  is_default={r.is_default}  is_signable={r.is_signable}"
                )
        except Exception as e:
            print(f"  [jwk_status]  ERROR: {e}")
        print()

        try:
            rows = db.execute(
                text(
                    "SELECT code, name, is_default, is_active FROM public.tenant_user_role ORDER BY code"
                )
            ).fetchall()
            print(f"  [tenant_user_role]  {len(rows)} row(s)")
            for r in rows:
                print(
                    f"    • {r.code}  '{r.name}'  is_default={r.is_default}  is_active={r.is_active}"
                )
        except Exception as e:
            print(f"  [tenant_user_role]  ERROR: {e}")
        print()

        try:
            rows = db.execute(
                text("""
                    SELECT operation_type, trigger_condition, severity, is_active
                    FROM public.sync_conflict_classification_matrix
                    WHERE tenant_id IS NULL
                    ORDER BY operation_type, trigger_condition
                """)
            ).fetchall()
            print(
                f"  [sync_conflict_classification_matrix]  {len(rows)} row(s) (null-tenant)"
            )
            for r in rows:
                print(
                    f"    • {r.operation_type:<20} {r.trigger_condition:<35}  → {r.severity}"
                )
        except Exception as e:
            print(f"  [sync_conflict_classification_matrix]  ERROR: {e}")
        print()

        try:
            rows = db.execute(
                text("""
                    SELECT template_code, channel, is_active
                    FROM public.communication_template
                    WHERE tenant_id IS NULL
                    ORDER BY template_code, channel
                """)
            ).fetchall()
            print(f"  [communication_template]  {len(rows)} row(s) (null-tenant)")
            for r in rows:
                print(f"    • {r.template_code:<35}  channel={r.channel}")
        except Exception as e:
            print(f"  [communication_template]  ERROR: {e}")
        print()

        try:
            rows = db.execute(
                text(
                    "SELECT template_id, display_name, category, is_active FROM public.email_template ORDER BY template_id"
                )
            ).fetchall()
            print(f"  [email_template]  {len(rows)} row(s)")
            for r in rows:
                print(
                    f"    • {r.template_id:<35}  '{r.display_name}'  category={r.category}"
                )
        except Exception as e:
            print(f"  [email_template]  ERROR: {e}")
        print()

        try:
            rows = db.execute(
                text(
                    "SELECT key, value_type, tenant_editable, category FROM public.platform_setting_catalog ORDER BY category, sort_order, key"
                )
            ).fetchall()
            print(f"  [platform_setting_catalog]  {len(rows)} row(s)")
            for r in rows:
                print(
                    f"    • {r.key:<50}  type={r.value_type:<10}  editable={r.tenant_editable}  cat={r.category}"
                )
        except Exception as e:
            print(f"  [platform_setting_catalog]  ERROR: {e}")
        print()

        try:
            rows = db.execute(
                text(
                    "SELECT key, value FROM public.platform_setting WHERE tenant_id IS NULL ORDER BY key"
                )
            ).fetchall()
            print(f"  [platform_setting (null-tenant defaults)]  {len(rows)} row(s)")
            for r in rows:
                print(f"    • {r.key:<50}  = {r.value}")
        except Exception as e:
            print(f"  [platform_setting (null-tenant defaults)]  ERROR: {e}")
        print()

        # SD-7 Batch 1: quote_template_line — grouped by template name
        try:
            rows = db.execute(
                text("""
                    SELECT qt.name AS template_name, COUNT(qtl.id) AS line_count
                    FROM public.quote_template qt
                    LEFT JOIN public.quote_template_line qtl ON qtl.quote_template_id = qt.id
                    GROUP BY qt.id, qt.name
                    ORDER BY qt.name
                """)
            ).fetchall()
            total_lines = sum(r.line_count for r in rows)
            print(
                f"  [quote_template_line]  {total_lines} row(s) across {len(rows)} template(s)"
            )
            for r in rows:
                print(f"    • '{r.template_name}'  lines={r.line_count}")
        except Exception as e:
            print(f"  [quote_template_line]  ERROR: {e}")


def mode_show():
    """Print what would be seeded without touching the DB."""
    print("=== seed_core: show mode ===\n")
    print(
        "Group A lookup tables (all ON CONFLICT DO NOTHING — safe to run on populated DB):\n"
    )

    all_rows = {**SIMPLE_CODE_TABLES, **TENANT_NULLABLE_CODE_TABLES}
    for table_name, defn in all_rows.items():
        print(f"  [{table_name}] — {len(defn['rows'])} rows:")
        for row in defn["rows"]:
            print(f"    • {row['code']}")
        print()

    print(
        f"  [entity_type] — {len(ENTITY_TYPE_ROWS)} rows: {', '.join(r['code'] for r in ENTITY_TYPE_ROWS)}"
    )
    print(
        f"  [platform_role] — {len(PLATFORM_ROLE_ROWS)} rows: {', '.join(r['code'] for r in PLATFORM_ROLE_ROWS)}"
    )
    print(
        f"  [job_expense_category] — {len(JOB_EXPENSE_CATEGORY_ROWS)} rows: {', '.join(r['code'] for r in JOB_EXPENSE_CATEGORY_ROWS)}"
    )
    print(
        f"  [qpl_contact_action_type] — {len(QPL_CONTACT_ACTION_ROWS)} rows: {', '.join(r['code'] for r in QPL_CONTACT_ACTION_ROWS)}"
    )
    print(
        f"  [notification_channel] — {len(NOTIFICATION_CHANNEL_DEF['rows'])} rows: "
        f"{', '.join(r['code'] for r in NOTIFICATION_CHANNEL_DEF['rows'])}"
    )
    print(
        "  [subscription_status] — seeded by seed_platform.py (6 rows: trialing, active, past_due, unpaid, canceled, paused)"
    )
    print(f"  [notification_category] — {len(NOTIFICATION_CATEGORY_ROWS)} rows")
    print(
        f"  [notification_default_policy] — {len(NOTIFICATION_DEFAULT_POLICY_ROWS)} rows (3 channels × 8 categories)"
    )
    print("  [app_service_category] — 1 row: accounting")
    print("  [app_service_provider] — 1 row: quickbooks")
    print(
        "  [app_service] — 1 global row: QuickBooks Online (deterministic UUID …000aa5)"
    )
    print(
        f"  [tax_rate_version] — {len(TAX_RATE_VERSION_ROWS)} rows (AppendOnly — no tenant_id):"
    )
    for trv in TAX_RATE_VERSION_ROWS:
        print(
            f"    • {trv['jurisdiction_code']:<20} {trv['rate_pct']}%  period={trv['valid_period']}  '{trv['description']}'"
        )
    print()

    # SD-01 new tables
    print(
        f"  [notification_category_sub_trigger] — {len(NOTIFICATION_CATEGORY_SUB_TRIGGER_ROWS)} rows:"
    )
    for r in NOTIFICATION_CATEGORY_SUB_TRIGGER_ROWS:
        print(f"    • {r['code']}")
    print()

    print(f"  [product_feature] — {len(PRODUCT_FEATURE_ROWS)} rows:")
    for r in PRODUCT_FEATURE_ROWS:
        print(f"    • {r['code']}  unit={r['unit']}")
    print()

    print(
        f"  [jwk_status] — {len(JWK_STATUS_ROWS)} rows (AppendOnly — created_at only):"
    )
    for r in JWK_STATUS_ROWS:
        print(f"    • {r['code']}")
    print()

    print(f"  [tenant_user_role] — {len(TENANT_USER_ROLE_ROWS)} rows:")
    for r in TENANT_USER_ROLE_ROWS:
        print(f"    • {r['code']}  (is_default={r['is_default']})")
    print()

    print(
        f"  [sync_conflict_classification_matrix] — {len(SYNC_CONFLICT_MATRIX_ROWS)} rows:"
    )
    for r in SYNC_CONFLICT_MATRIX_ROWS:
        print(
            f"    • {r['operation_type']}/{r['trigger_condition']}  → {r['severity']}"
        )
    print()

    print(f"  [communication_template] — {len(COMMUNICATION_TEMPLATE_ROWS)} rows:")
    for r in COMMUNICATION_TEMPLATE_ROWS:
        print(f"    • {r['template_code']}/{r['channel']}")
    print()

    email_templates = _load_email_templates()
    print(
        f"  [email_template] — {len(email_templates)} templates (loaded from data/email_templates/*.json):"
    )
    for t in email_templates:
        print(
            f"    • {t['template_id']}  '{t['display_name']}'  category={t['category']}"
        )
    print()

    print(f"  [platform_setting_catalog] — {len(PLATFORM_SETTING_CATALOG_ROWS)} rows")
    print(
        f"  [platform_setting (null-tenant defaults)] — {len(PLATFORM_SETTING_DEFAULTS)} rows"
    )

    # CLASS-B1: job_type platform defaults
    job_type_show = [
        ("service_call", "Service Call", 10),
        ("troubleshoot", "Troubleshoot / Diagnostic", 20),
        ("panel_upgrade", "Panel Upgrade", 30),
        ("rewire", "Rewire", 40),
        ("lighting", "Lighting", 50),
        ("generator_install", "Generator Install", 60),
        ("ev_charger_install", "EV Charger Install", 70),
        ("new_construction", "New Construction", 80),
        ("inspection", "Inspection", 90),
        ("warranty", "Warranty", 100),
        ("other", "Other", 999),
    ]
    print(
        f"\n  [job_type] — {len(job_type_show)} platform-default rows (tenant_id=NULL):"
    )
    for code, label, sort_order in job_type_show:
        print(f"    • {code:<22} sort={sort_order:<4}  '{label}'")


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "A", "seed_core.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if args.mode in ("seed", "inspect"):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_core.py")
    if args.mode == "seed":
        mode_seed()
    elif args.mode == "inspect":
        mode_inspect()
    elif args.mode == "show":
        mode_show()
