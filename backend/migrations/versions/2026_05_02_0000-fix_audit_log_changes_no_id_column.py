"""fix_audit_log_changes_no_id_column

Revision ID: fix_audit_log_changes_no_id
Revises: 0b308320879f
Create Date: 2026-05-02 00:00:00

Fix audit.log_changes() trigger function to handle tables whose primary key
is not named 'id' (e.g. tenant_settings uses tenant_id as its PK).

The previous implementation used ``COALESCE(NEW.id, OLD.id)::text`` directly
which crashes with "record has no field id" for any table that lacks an 'id'
column.  This patch wraps the entity_id extraction with the same
``EXCEPTION WHEN undefined_column`` guard already used for tenant_id,
falling back first to tenant_id and then to NULL.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_audit_log_changes_no_id"
down_revision = "0b308320879f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit.log_changes()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $func$
            DECLARE
                v_user_id uuid;
                v_actor_type text;
                v_tenant_id uuid;
                v_entity_id text;
            BEGIN
                -- Read user_id from session variable (set by application)
                -- Falls back to system UUID if not set (background jobs, migrations)
                v_user_id := COALESCE(
                    NULLIF(current_setting('app.user_id', true), '')::uuid,
                    '00000000-0000-0000-0000-000000000000'::uuid
                );

                -- Determine actor_type based on user_id
                IF v_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
                    v_actor_type := 'system';
                ELSE
                    v_actor_type := 'user';
                END IF;

                -- Safely extract tenant_id (handles tables without tenant_id column)
                -- For tables without tenant_id (contact, address), this will be NULL
                BEGIN
                    v_tenant_id := COALESCE(NEW.tenant_id, OLD.tenant_id);
                EXCEPTION
                    WHEN undefined_column THEN
                        v_tenant_id := NULL;
                END;

                -- Safely extract entity_id.
                -- Some tables (e.g. tenant_settings) use a non-'id' primary key.
                -- Fallback chain: id -> tenant_id -> NULL
                BEGIN
                    v_entity_id := COALESCE(NEW.id, OLD.id)::text;
                EXCEPTION
                    WHEN undefined_column THEN
                        BEGIN
                            v_entity_id := COALESCE(NEW.tenant_id, OLD.tenant_id)::text;
                        EXCEPTION
                            WHEN undefined_column THEN
                                v_entity_id := NULL;
                        END;
                END;

                -- Insert audit event record capturing the change
                INSERT INTO audit.event (
                    tenant_id,
                    user_id,
                    actor_type,
                    entity_name,
                    entity_id,
                    action,
                    old_values,
                    new_values,
                    occurred_at
                ) VALUES (
                    v_tenant_id,
                    v_user_id,
                    v_actor_type,
                    TG_TABLE_NAME::text,
                    v_entity_id,
                    TG_OP,
                    CASE
                        WHEN TG_OP IN ('DELETE', 'UPDATE') THEN row_to_json(OLD)::jsonb
                        ELSE NULL
                    END,
                    CASE
                        WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb
                        ELSE NULL
                    END,
                    NOW()
                );

                -- Return the appropriate record to allow the operation to complete
                RETURN COALESCE(NEW, OLD);
            END;
        $func$;
        """
    )


def downgrade() -> None:
    # Restore previous version (entity_id without guard — matches original)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit.log_changes()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $func$
            DECLARE
                v_user_id uuid;
                v_actor_type text;
                v_tenant_id uuid;
            BEGIN
                v_user_id := COALESCE(
                    NULLIF(current_setting('app.user_id', true), '')::uuid,
                    '00000000-0000-0000-0000-000000000000'::uuid
                );
                IF v_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
                    v_actor_type := 'system';
                ELSE
                    v_actor_type := 'user';
                END IF;
                BEGIN
                    v_tenant_id := COALESCE(NEW.tenant_id, OLD.tenant_id);
                EXCEPTION
                    WHEN undefined_column THEN
                        v_tenant_id := NULL;
                END;
                INSERT INTO audit.event (
                    tenant_id, user_id, actor_type, entity_name, entity_id, action,
                    old_values, new_values, occurred_at
                ) VALUES (
                    v_tenant_id, v_user_id, v_actor_type, TG_TABLE_NAME::text,
                    COALESCE(NEW.id, OLD.id)::text,
                    TG_OP,
                    CASE WHEN TG_OP IN ('DELETE', 'UPDATE') THEN row_to_json(OLD)::jsonb ELSE NULL END,
                    CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb ELSE NULL END,
                    NOW()
                );
                RETURN COALESCE(NEW, OLD);
            END;
        $func$;
        """
    )
