"""fix_user_endpoint_guard_trigger_logic

Revision ID: 102c1d8d3d4a
Revises: 6907731fd637
Create Date: 2026-03-30 18:19:08.212000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "102c1d8d3d4a"
down_revision: str | None = "6907731fd637"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Fix the guard_user_endpoint_primary_email function to avoid recursive trigger issues
    # The fix uses a session variable to bypass the Highlander check during auto-demotion
    op.execute("""
        CREATE OR REPLACE FUNCTION guard_user_endpoint_primary_email() 
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          has_other_primary boolean;
          bypass_check text;
        BEGIN
          IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
            IF NEW.channel = 'email' THEN
              NEW.value := lower(trim(NEW.value));
              
              -- If this endpoint is being set to primary
              IF COALESCE(NEW.is_primary, false) AND NOT COALESCE(OLD.is_primary, false) THEN
                -- Set bypass flag so auto-demotion doesn't trigger Highlander check
                PERFORM set_config('aevofab.bypassing_primary_check', 'true', true);
                
                -- Auto-demote any existing primary emails for this user
                UPDATE user_endpoint 
                   SET is_primary = false, updated_at = now() 
                 WHERE user_id = NEW.user_id 
                   AND channel = 'email' 
                   AND is_primary = true 
                   AND id <> NEW.id;
                
                -- Clear bypass flag
                PERFORM set_config('aevofab.bypassing_primary_check', NULL, true);
              END IF;

              -- Prevent demoting the ONLY primary email manually (unless we're in bypass mode)
              bypass_check := current_setting('aevofab.bypassing_primary_check', true);
              IF bypass_check IS NULL OR bypass_check <> 'true' THEN
                IF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                  SELECT EXISTS (
                    SELECT 1 FROM user_endpoint
                     WHERE user_id = NEW.user_id AND channel='email' AND is_primary = true AND id <> NEW.id
                  ) INTO has_other_primary;
                  IF NOT has_other_primary THEN
                    RAISE EXCEPTION 'Cannot demote the only primary email endpoint for this user'
                      USING ERRCODE = '23514', HINT = 'Promote a different email endpoint first.';
                  END IF;
                END IF;
              END IF;
            END IF;
            RETURN NEW;

          ELSIF TG_OP = 'DELETE' THEN
            IF OLD.channel = 'email' AND COALESCE(OLD.is_primary, false) THEN
              SELECT EXISTS (
                SELECT 1 FROM user_endpoint
                 WHERE user_id = OLD.user_id AND channel='email' AND is_primary = true AND id <> OLD.id
              ) INTO has_other_primary;
              IF NOT has_other_primary THEN
                RAISE EXCEPTION 'Cannot delete the only primary email endpoint for this user'
                  USING ERRCODE = '23514', HINT = 'Promote another email endpoint first.';
              END IF;
            END IF;
            RETURN OLD;
          END IF;

          RETURN COALESCE(NEW, OLD);
        END;$$
    """)


def downgrade() -> None:
    # Revert to the original buggy version (this shouldn't normally be needed)
    op.execute("""
        CREATE OR REPLACE FUNCTION guard_user_endpoint_primary_email() 
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          has_other_primary boolean;
        BEGIN
          IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
            IF NEW.channel = 'email' THEN
              NEW.value := lower(trim(NEW.value));
              
              -- If this endpoint is being set to primary
              IF COALESCE(NEW.is_primary, false) AND NOT COALESCE(OLD.is_primary, false) THEN
                -- Auto-demote any existing primary emails for this user
                UPDATE user_endpoint 
                   SET is_primary = false, updated_at = now() 
                 WHERE user_id = NEW.user_id 
                   AND channel = 'email' 
                   AND is_primary = true 
                   AND id <> NEW.id;
              END IF;

              -- Prevent demoting the ONLY primary email manually
              IF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                SELECT EXISTS (
                  SELECT 1 FROM user_endpoint
                   WHERE user_id = NEW.user_id AND channel='email' AND is_primary = true AND id <> NEW.id
                ) INTO has_other_primary;
                IF NOT has_other_primary THEN
                  RAISE EXCEPTION 'Cannot demote the only primary email endpoint for this user'
                    USING ERRCODE = '23514', HINT = 'Promote a different email endpoint first.';
                END IF;
              END IF;
            END IF;
            RETURN NEW;

          ELSIF TG_OP = 'DELETE' THEN
            IF OLD.channel = 'email' AND COALESCE(OLD.is_primary, false) THEN
              SELECT EXISTS (
                SELECT 1 FROM user_endpoint
                 WHERE user_id = OLD.user_id AND channel='email' AND is_primary = true AND id <> OLD.id
              ) INTO has_other_primary;
              IF NOT has_other_primary THEN
                RAISE EXCEPTION 'Cannot delete the only primary email endpoint for this user'
                  USING ERRCODE = '23514', HINT = 'Promote another email endpoint first.';
              END IF;
            END IF;
            RETURN OLD;
          END IF;

          RETURN COALESCE(NEW, OLD);
        END;$$
    """)
