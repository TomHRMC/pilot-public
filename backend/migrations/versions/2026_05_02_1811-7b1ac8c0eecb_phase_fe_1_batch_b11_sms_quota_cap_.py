"""phase_fe_1_batch_b11_sms_quota_cap_policy_setting

Revision ID: 7b1ac8c0eecb
Revises: 6960f3f4ddd2
Create Date: 2026-05-02 18:11:34

B11/A65 / Migration 6 — Settings catalog entry for sms_quota_cap_policy.

DEVIATION FROM DESIGN DOC:
  The design doc (§A.6) specified inserting a row into `settings_catalog`,
  but MCP query confirmed that table does NOT exist in the live database.
  B9 implemented tenant settings via `tenant_settings` (a fixed-column model)
  rather than a key-value `settings_catalog` table.

  Decision: sms_quota.check_quota() uses a hardcoded fallback of 'soft' for MVP.
  The cap_policy is stored per-period in sms_quota_period.cap_policy and is set
  at period creation time. No catalog entry is needed at this stage.

  This migration is a documented no-op (structural placeholder in the chain).
  A future batch can add cap_policy configuration to the tenant settings model
  as a proper column if needed.
"""

# revision identifiers, used by Alembic.
revision = "7b1ac8c0eecb"
down_revision = "6960f3f4ddd2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: settings_catalog table does not exist (B9 used tenant_settings model instead).
    # sms_quota_cap_policy defaults to 'soft' hardcoded in services/sms_quota.py.
    pass


def downgrade() -> None:
    pass
