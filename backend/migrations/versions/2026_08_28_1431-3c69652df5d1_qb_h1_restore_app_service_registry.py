"""qb_h1_restore_app_service_registry

QuickBooks coverage audit + sync hardening (QB-H1) — registry restoration.

This data-only migration is the **prod recovery path** for the app_service*
registry (prod has 0 rows — schema-restore + alembic stamp never executed
dd4ed7ed5f3b's embedded INSERTs) and the dev reconciliation of the
intuit/quickbooks provider split.

Canonical provider_code is ``quickbooks`` (design §G Q1 — deliberate,
evidence-based deviation from the launch-plan card's parenthetical ``intuit``;
~30 application call sites query ``provider_code == "quickbooks"``, zero use
``intuit``).

See: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §B.3

Revision ID: 3c69652df5d1
Revises: 58c3ad26129f
Create Date: 2026-08-28 14:31:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "3c69652df5d1"
down_revision = "58c3ad26129f"
branch_labels = None
depends_on = None


# Deterministic UUID for the global app_service row (seed parity — design §B.4).
# Does NOT collide with reserved ...0001–...0005 seed families (README-seed-data).
GLOBAL_APP_SERVICE_ID = "00000000-0000-0000-0000-000000000aa5"

# Notification template copy — byte-identical to seed_platform.py (design §F.3).
# Channel: email
_EXPIRED_EMAIL_SUBJECT = "[QuickBooks] Connection expired — reconnect to resume sync"
_EXPIRED_EMAIL_BODY = (
    "Your QuickBooks Online connection for {{tenant_name}} has expired. "
    "The refresh token was rejected by Intuit, so customer, invoice, and payment "
    "sync is paused. No data was lost — queued changes will resume automatically "
    "after you reconnect. Go to Settings → Integrations → QuickBooks → Reconnect."
)
# Channel: in_app
_EXPIRED_INAPP_SUBJECT = _EXPIRED_EMAIL_SUBJECT
_EXPIRED_INAPP_BODY = (
    "QuickBooks connection expired for {{tenant_name}}. "
    "Sync is paused — reconnect in Settings → Integrations → QuickBooks."
)
# Channel: push
_EXPIRED_PUSH_SUBJECT = _EXPIRED_EMAIL_SUBJECT
_EXPIRED_PUSH_BODY = "QuickBooks connection expired — tap to reconnect and resume sync."


def upgrade() -> None:
    # Data-migration standard: disable FK triggers for the duration of the
    # transaction so the global-row DELETE+INSERT pair is safe regardless of
    # any stale references. Re-enabled at end of transaction.
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. app_service_category (code PK) — idempotent
    op.execute(
        """
        INSERT INTO app_service_category (code, description, is_active, created_at, updated_at)
        VALUES ('accounting', 'Accounting & Bookkeeping integrations', true, now(), now())
        ON CONFLICT DO NOTHING;
        """
    )

    # 2. app_service_provider (code PK) — canonize 'quickbooks'
    op.execute(
        """
        INSERT INTO app_service_provider (code, description, is_active, created_at, updated_at)
        VALUES ('quickbooks', 'QuickBooks Online (Intuit)', true, now(), now())
        ON CONFLICT DO NOTHING;
        """
    )

    # 3. Dev reconcile: re-point any global 'intuit' row to 'quickbooks'
    #    (no-op in prod — 0 rows there)
    op.execute(
        """
        UPDATE app_service
        SET provider_code = 'quickbooks', updated_at = now()
        WHERE tenant_id IS NULL AND provider_code = 'intuit';
        """
    )

    # 4. Orphan retire: delete the 'intuit' provider row only if nothing references it
    op.execute(
        """
        DELETE FROM app_service_provider
        WHERE code = 'intuit'
          AND NOT EXISTS (
              SELECT 1 FROM app_service WHERE provider_code = 'intuit'
          );
        """
    )

    # 5. Normalize the global row to the deterministic UUID (seed parity).
    #    Safe: the global row is a pure catalog entry — nothing references it
    #    (integration_credential / integration_sync_mapping point at tenant-scoped
    #    rows; verified via MCP pre-work: 0 cred_refs, 0 map_refs).
    op.execute(
        """
        DELETE FROM app_service
        WHERE tenant_id IS NULL
          AND category_code = 'accounting'
          AND provider_code = 'quickbooks';
        """
    )
    op.execute(
        f"""
        INSERT INTO app_service
            (id, tenant_id, name, category_code, provider_code,
             is_active, external_account_id, created_at, updated_at)
        VALUES
            ('{GLOBAL_APP_SERVICE_ID}', NULL, 'QuickBooks Online',
             'accounting', 'quickbooks', true, NULL, now(), now());
        """
    )

    # 6. notification_type: qb_connection_expired (code PK) — idempotent
    op.execute(
        """
        INSERT INTO notification_type
            (code, name, audience, is_active, created_at, updated_at)
        VALUES
            ('qb_connection_expired', 'QuickBooks Connection Expired',
             'tenant', true, now(), now())
        ON CONFLICT DO NOTHING;
        """
    )

    # 7. Three notification_template rows (email / in_app / push, tenant_id NULL,
    #    locale 'en') — each guarded by WHERE NOT EXISTS on the natural key.
    _insert_template("email", _EXPIRED_EMAIL_SUBJECT, _EXPIRED_EMAIL_BODY)
    _insert_template("in_app", _EXPIRED_INAPP_SUBJECT, _EXPIRED_INAPP_BODY)
    _insert_template("push", _EXPIRED_PUSH_SUBJECT, _EXPIRED_PUSH_BODY)


def _insert_template(channel: str, subject: str, body: str) -> None:
    """Insert a qb_connection_expired template row, idempotent on the natural key."""
    op.execute(
        f"""
        INSERT INTO notification_template
            (id, tenant_id, notification_type_code, channel, locale,
             subject, body, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), NULL, 'qb_connection_expired',
               '{channel}', 'en',
               '{_esc(subject)}', '{_esc(body)}', true, now(), now()
        WHERE NOT EXISTS (
            SELECT 1 FROM notification_template
            WHERE notification_type_code = 'qb_connection_expired'
              AND channel = '{channel}'
              AND locale = 'en'
              AND tenant_id IS NULL
        );
        """
    )


def _esc(s: str) -> str:
    """Escape single quotes for safe embedding in SQL string literals."""
    return s.replace("'", "''")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Reverse 7: delete the 3 qb_connection_expired templates (value-scoped)
    op.execute(
        """
        DELETE FROM notification_template
        WHERE notification_type_code = 'qb_connection_expired'
          AND tenant_id IS NULL;
        """
    )

    # Reverse 6: delete the qb_connection_expired notification_type
    op.execute("DELETE FROM notification_type WHERE code = 'qb_connection_expired';")

    # Reverse 5: delete the deterministic global row by PK
    op.execute(
        f"""
        DELETE FROM app_service
        WHERE id = '{GLOBAL_APP_SERVICE_ID}';
        """
    )

    # Reverse 4: re-insert the 'intuit' provider row (the orphan-retire reverse)
    op.execute(
        """
        INSERT INTO app_service_provider (code, description, is_active, created_at, updated_at)
        VALUES ('intuit', 'Intuit (QuickBooks Online)', true, now(), now())
        ON CONFLICT DO NOTHING;
        """
    )

    # Reverse 3: re-point the global row back to 'intuit' (best-effort — the
    # pre-migration random-UUID dev row is not restorable; it is re-created by
    # the forward path. This is acceptable per design §B.3.)
    # No-op in prod (0 rows). In dev, the global row was deleted in step 5 and
    # not re-created here — documented as acceptable.
