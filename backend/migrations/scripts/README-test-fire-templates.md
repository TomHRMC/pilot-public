# test_fire_templates.py — QA Tool Reference

**Location**: `backend/migrations/scripts/test_fire_templates.py`
**Type**: Standalone CLI QA tool
**Added**: SD-8 (2026-07-23), `--db-update` added 2026-07-24

---

## What It Does

Manually fires one email template or notification template through the real SendGrid integration for QA verification. It renders the template with hardcoded test-data placeholders and either prints the rendered output (`--dry-run`) or sends a real email.

**Not part of the seed system.** This script is:
- NOT registered in `reset_dev_db.py`
- NOT called by any automated test or CI pipeline
- NOT called by `seed_e2e_db.py`
- Safe to run at any time without affecting seed data

---

## Prerequisites

```bash
# Run from the backend/ directory with the venv activated
cd /path/to/pilot/backend
source .venv/bin/activate
```

The script requires a running local PostgreSQL database (for template lookup). If `SENDGRID_API_KEY` is not set in `.env`, sends are mocked — the script will print `Mocked successful send` and return `status=sent`.

---

## Template Catalog Cache

The script stores a snapshot of all available templates in [`data/template_catalog.json`](data/template_catalog.json). This file:

- Drives the `--help` template lists — so you can see all options without connecting to the DB
- Is refreshed on demand via `--db-update`
- Is committed to the repo so it works even without a local DB connection

### Refresh the catalog from the live DB

```bash
python migrations/scripts/test_fire_templates.py --db-update
```

Output:
```
=== test_fire_templates.py --db-update ===

  Querying live DB to refresh: migrations/scripts/data/template_catalog.json

  ✅ email_template        — 16 rows
  ✅ notification_template — 9 type codes
  ✅ communication_template — 11 template codes

  Written to: /path/to/backend/migrations/scripts/data/template_catalog.json
  Run --help to see the updated catalog.
```

Run `--db-update` whenever:
- New email templates are added via migration
- New notification types are added to `notification_template`
- New communication templates are seeded

---

## Usage

### Fire an `email_template` by template ID (dry run)

```bash
python migrations/scripts/test_fire_templates.py \
    --email-template invoice_sent \
    --recipient tom@pilotfortrades.com \
    --dry-run
```

### Fire an `email_template` via SendGrid (real send)

```bash
python migrations/scripts/test_fire_templates.py \
    --email-template invoice_sent \
    --recipient tom@pilotfortrades.com
```

### Fire a `notification_template` by type code

```bash
python migrations/scripts/test_fire_templates.py \
    --template-type quote_accepted \
    --channel email \
    --recipient tom@pilotfortrades.com
```

### Fire a `notification_template` with dry run and custom locale

```bash
python migrations/scripts/test_fire_templates.py \
    --template-type dunning_reminder \
    --channel email \
    --recipient tom@pilotfortrades.com \
    --locale en \
    --dry-run
```

### Show full help

```bash
python migrations/scripts/test_fire_templates.py --help
```

---

## Arguments

| Argument | Type | Required | Default | Description |
|:---|:---|:---|:---|:---|
| `--email-template` | str | One of these three | — | `template_id` from `email_template` table (e.g. `invoice_sent`) |
| `--template-type` | str | One of these three | — | `notification_type_code` from `notification_template` table (e.g. `quote_accepted`) |
| `--db-update` | flag | One of these three | — | Refresh `data/template_catalog.json` from live DB and exit. No `--recipient` required. |
| `--channel` | str | No | `email` | Delivery channel. Only `email` is supported in this version. |
| `--recipient` | str | Required for fire modes | — | Email address to send to (not needed for `--db-update`) |
| `--tenant-id` | str | No | `settings.TEST_TENANT_ID` | UUID of tenant for template lookup |
| `--locale` | str | No | `en` | Locale for `notification_template` lookup |
| `--dry-run` | flag | No | False | Render and print without sending |

---

## Available Templates

### `email_template` IDs

Query the DB to see all available templates:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from migrations.scripts._db_utils import get_db_session
from sqlalchemy import text
with get_db_session() as db:
    rows = db.execute(text('SELECT template_id, display_name, is_active FROM public.email_template ORDER BY template_id')).fetchall()
    for r in rows:
        active = '✅' if r.is_active else '❌'
        print(f'  {active} {r.template_id:<42} {r.display_name}')
"
```

As of SD-8, the 16 available templates are:

| template_id | Display Name |
|:---|:---|
| `email_verification` | Email Verification |
| `invoice_sent` | Invoice Sent |
| `mfa_reset_by_owner` | MFA Reset by Owner |
| `password_reset` | Password Reset |
| `payment_failed` | Payment Failed |
| `payment_received_customer` | Payment Received (Customer) |
| `payment_received_tenant` | Payment Received (Tenant) |
| `quote_accepted` | Quote Accepted |
| `quote_declined` | Quote Declined |
| `quote_expiring` | Quote Expiring |
| `quote_sent` | Quote Sent |
| `subscription_payment_failed` | Subscription Payment Failed |
| `subscription_renewal` | Subscription Renewal |
| `trial_expired` | Trial Expired |
| `trial_expiring` | Trial Expiring |
| `welcome` | Welcome |

### `notification_template` type codes

As of SD-8, the 9 available notification type codes (email channel):

| type_code | Description |
|:---|:---|
| `customer_communication_sent` | Customer sent a message |
| `dunning_reminder` | Overdue invoice reminder |
| `gps_variance_alert` | Tech GPS location anomaly |
| `job_assigned` | Job assigned to tech |
| `qb_conflict_pre_warning` | QuickBooks sync pre-conflict warning |
| `qb_sync_conflict` | QuickBooks sync conflict detected |
| `quote_accepted` | Customer accepted a quote |
| `schedule_changed` | Job schedule changed |
| `system_template_updated` | Platform notification template updated |

---

## Output Format

```
=== test_fire_templates.py ===
Template type : email_template / invoice_sent
Channel       : email
Recipient     : tom@pilotfortrades.com
Tenant        : 00000000-0000-0000-0000-000000000001
Dry run       : True

[RENDERED SUBJECT]
Invoice from Pilot Dev Tenant — $955.96 due 2026-08-22

[RENDERED BODY (first 200 chars)]
Hi Dev Owner (Test Send),

Your invoice from Pilot Dev Tenant is ready...

[DRY RUN — not sent]
```

On real send (without `--dry-run`):

```
Sending via SendGrid...
✅ Send result: {'status': 'sent', 'http_status': 202}
```

---

## Variable Substitution

The script uses a hardcoded `TEST_RENDER_CONTEXT` dict — it does NOT query real entity data from the DB. All variables are test placeholders:

| Variable | Value |
|:---|:---|
| `customer_name` | Dev Owner (Test Send) |
| `company_name` | Pilot Dev Tenant |
| `invoice_total` | 955.96 |
| `invoice_url` | https://app.pilotfortrades.com/invoices/test-preview |
| `due_date` | 2026-08-22 |
| `quote_number` | QUO-900004 |
| `quote_url` | https://app.pilotfortrades.com/quotes/test-preview |
| `quote_total` | 1200.00 |
| `job_title` | Panel Upgrade — Test Send |
| ... | (see `TEST_RENDER_CONTEXT` in the script for full list) |

Unresolved template variables are left as `{variable_name}` (no error raised).

---

## Error Cases

| Condition | Output | Exit code |
|:---|:---|:---|
| `--email-template` not found in DB | `❌ email_template 'X' not found in DB.` | 1 |
| `--email-template` is disabled | `❌ email_template 'X' is disabled (is_active=False).` | 1 |
| `--template-type` not found | `❌ notification_template not found: type_code='X' channel='email' locale='en'` | 1 |
| Non-email channel | `❌ Only 'email' channel is supported in this version.` | 1 |
| SendGrid returns error | `❌ Send failed: {...}` | 1 |
| Success | `✅ Send result: {...}` | 0 |

---

## Future Additions

Push/in_app/SMS channel support will be added in a later batch. The architecture is in place — only the `_fire_*` functions need to be extended per channel.

---

## Related Files

| File | Description |
|:---|:---|
| [`migrations/scripts/test_fire_templates.py`](test_fire_templates.py) | This script |
| [`migrations/scripts/data/template_catalog.json`](data/template_catalog.json) | Cached template catalog — drives `--help` lists; refresh with `--db-update` |
| [`services/email_template_renderer.py`](../../services/email_template_renderer.py) | `render_and_send()` — the underlying renderer |
| [`services/email_service.py`](../../services/email_service.py) | `send_email()` — SendGrid dispatch |
| [`migrations/scripts/data/email_templates/`](data/email_templates/) | JSON source files for email template bodies |
| [`backend/README-seed-data.md`](../../README-seed-data.md) | Seed system reference — §2 script inventory |
