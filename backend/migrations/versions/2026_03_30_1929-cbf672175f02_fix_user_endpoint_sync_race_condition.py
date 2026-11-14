"""fix_user_endpoint_sync_race_condition

Revision ID: cbf672175f02
Revises: 102c1d8d3d4a
Create Date: 2026-03-30 19:29:32.532135+00:00

Fix the race condition in sync_user_email_from_endpoint_fn() where auto-demotion
of the old primary triggers a sync before the new primary is visible, causing
a NULL constraint violation on user.email.

The fix adds a session variable check to skip the sync during auto-demotion,
allowing the sync to happen when the new primary is promoted instead.

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cbf672175f02"
down_revision: str | None = "102c1d8d3d4a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Update sync_user_email_from_endpoint_fn to check session variable before syncing
    # when an endpoint is demoted. This prevents the race condition where the function
    # tries to find the next primary before the new primary is committed.
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_user_email_from_endpoint_fn()
        RETURNS TRIGGER AS $$
        DECLARE
            next_primary_email TEXT;
            skip_sync TEXT;
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                -- If inserting a primary email endpoint, sync to user table
                IF NEW.channel = 'email' AND COALESCE(NEW.is_primary, false) THEN
                    UPDATE "user"
                    SET email = LOWER(NEW.value),
                        updated_at = NOW()
                    WHERE id = NEW.user_id;
                END IF;
                RETURN NEW;
                
            ELSIF (TG_OP = 'UPDATE') THEN
                -- If updating to primary email or changing primary email value
                IF NEW.channel = 'email' THEN
                    IF COALESCE(NEW.is_primary, false) AND 
                       (NOT COALESCE(OLD.is_primary, false) OR NEW.value IS DISTINCT FROM OLD.value) THEN
                        UPDATE "user"
                        SET email = LOWER(NEW.value),
                            updated_at = NOW()
                        WHERE id = NEW.user_id;
                    ELSIF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                        -- Primary was demoted - check if we should skip sync during auto-demotion
                        skip_sync := current_setting('aevofab.skip_sync', true);
                        IF skip_sync IS NULL OR skip_sync != 'true' THEN
                            -- Find next primary email
                            SELECT LOWER(value) INTO next_primary_email
                            FROM user_endpoint
                            WHERE user_id = OLD.user_id
                              AND channel = 'email'
                              AND is_primary = true
                            ORDER BY created_at DESC
                            LIMIT 1;
                            
                            UPDATE "user"
                            SET email = next_primary_email,
                                updated_at = NOW()
                            WHERE id = OLD.user_id;
                        END IF;
                        -- If skip_sync is true, do nothing - the sync will happen when new primary is promoted
                    END IF;
                END IF;
                RETURN NEW;
                
            ELSIF (TG_OP = 'DELETE') THEN
                -- If deleting primary email, find next available primary
                IF OLD.channel = 'email' AND COALESCE(OLD.is_primary, false) THEN
                    SELECT LOWER(value) INTO next_primary_email
                    FROM user_endpoint
                    WHERE user_id = OLD.user_id
                      AND channel = 'email'
                      AND is_primary = true
                      AND id != OLD.id  -- Exclude the one being deleted
                    ORDER BY created_at DESC
                    LIMIT 1;
                    
                    UPDATE "user"
                    SET email = next_primary_email,
                        updated_at = NOW()
                    WHERE id = OLD.user_id;
                END IF;
                RETURN OLD;
            END IF;

            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Update guard_user_endpoint_primary_email to set skip_sync flag during auto-demotion
    op.execute("""
        CREATE OR REPLACE FUNCTION guard_user_endpoint_primary_email() 
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          has_other_primary boolean;
          skip_check TEXT;
        BEGIN
          IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
            IF NEW.channel = 'email' THEN
              NEW.value := lower(trim(NEW.value));
              
              -- If this endpoint is being set to primary
              IF COALESCE(NEW.is_primary, false) AND NOT COALESCE(OLD.is_primary, false) THEN
                -- Set both flags to prevent race conditions during auto-demotion
                PERFORM set_config('aevofab.skip_sync', 'true', true);
                PERFORM set_config('aevofab.skip_highlander_check', 'true', true);
                
                -- Auto-demote any existing primary emails for this user
                UPDATE user_endpoint
                   SET is_primary = false, updated_at = now()
                 WHERE user_id = NEW.user_id
                   AND channel = 'email'
                   AND is_primary = true
                   AND id <> NEW.id;
                
                -- Clear both flags
                PERFORM set_config('aevofab.skip_sync', NULL, true);
                PERFORM set_config('aevofab.skip_highlander_check', NULL, true);
              END IF;

              -- Prevent demoting the ONLY primary email manually
              IF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                -- Check if we're in auto-demotion mode (bypass check)
                skip_check := current_setting('aevofab.skip_highlander_check', true);
                IF skip_check IS NULL OR skip_check != 'true' THEN
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
    # Restore original sync function without skip_sync check
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_user_email_from_endpoint_fn()
        RETURNS TRIGGER AS $$
        DECLARE
            next_primary_email TEXT;
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                -- If inserting a primary email endpoint, sync to user table
                IF NEW.channel = 'email' AND COALESCE(NEW.is_primary, false) THEN
                    UPDATE "user"
                    SET email = LOWER(NEW.value),
                        updated_at = NOW()
                    WHERE id = NEW.user_id;
                END IF;
                RETURN NEW;
                
            ELSIF (TG_OP = 'UPDATE') THEN
                -- If updating to primary email or changing primary email value
                IF NEW.channel = 'email' THEN
                    IF COALESCE(NEW.is_primary, false) AND 
                       (NOT COALESCE(OLD.is_primary, false) OR NEW.value IS DISTINCT FROM OLD.value) THEN
                        UPDATE "user"
                        SET email = LOWER(NEW.value),
                            updated_at = NOW()
                        WHERE id = NEW.user_id;
                    ELSIF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                        -- Primary was demoted, find next primary email
                        SELECT LOWER(value) INTO next_primary_email
                        FROM user_endpoint
                        WHERE user_id = OLD.user_id
                          AND channel = 'email'
                          AND is_primary = true
                        ORDER BY created_at DESC
                        LIMIT 1;
                        
                        UPDATE "user"
                        SET email = next_primary_email,
                            updated_at = NOW()
                        WHERE id = OLD.user_id;
                    END IF;
                END IF;
                RETURN NEW;
                
            ELSIF (TG_OP = 'DELETE') THEN
                -- If deleting primary email, find next available primary
                IF OLD.channel = 'email' AND COALESCE(OLD.is_primary, false) THEN
                    SELECT LOWER(value) INTO next_primary_email
                    FROM user_endpoint
                    WHERE user_id = OLD.user_id
                      AND channel = 'email'
                      AND is_primary = true
                      AND id != OLD.id  -- Exclude the one being deleted
                    ORDER BY created_at DESC
                    LIMIT 1;
                    
                    UPDATE "user"
                    SET email = next_primary_email,
                        updated_at = NOW()
                    WHERE id = OLD.user_id;
                END IF;
                RETURN OLD;
            END IF;

            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Restore original guard function from migration 102c1d8d3d4a
    op.execute("""
        CREATE OR REPLACE FUNCTION guard_user_endpoint_primary_email() 
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          has_other_primary boolean;
          skip_check TEXT;
        BEGIN
          IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
            IF NEW.channel = 'email' THEN
              NEW.value := lower(trim(NEW.value));
              
              -- If this endpoint is being set to primary
              IF COALESCE(NEW.is_primary, false) AND NOT COALESCE(OLD.is_primary, false) THEN
                -- Set session variable to bypass Highlander check during auto-demotion
                PERFORM set_config('aevofab.skip_highlander_check', 'true', true);
                
                -- Auto-demote any existing primary emails for this user
                UPDATE user_endpoint 
                   SET is_primary = false, updated_at = now() 
                 WHERE user_id = NEW.user_id 
                   AND channel = 'email' 
                   AND is_primary = true 
                   AND id <> NEW.id;
                
                -- Clear the bypass flag
                PERFORM set_config('aevofab.skip_highlander_check', NULL, true);
              END IF;

              -- Prevent demoting the ONLY primary email manually
              IF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                -- Check if we're in auto-demotion mode (bypass check)
                skip_check := current_setting('aevofab.skip_highlander_check', true);
                IF skip_check IS NULL OR skip_check != 'true' THEN
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
