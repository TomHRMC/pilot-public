"""phase_fe_1_batch_b16_fix_audit_log_changes_for_text_pks

Revision ID: 6350c51bc555
Revises: 0c8ae7d64a43
Create Date: 2026-05-03 22:10:20

Fixes audit.log_changes() to handle tables where the PK is not named 'id' and
there is no 'tenant_id' column (e.g., help_article.article_id).

The original fallback chain returned NULL which violates the NOT NULL constraint
on audit.event.entity_id. The fix extends the chain with a final fallback to
the TG_TABLE_NAME string prefixed with 'unknown_' so the constraint is never
violated.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6350c51bc555"
down_revision = "0c8ae7d64a43"
branch_labels = None
depends_on = None

# The updated function extends the fallback chain to never produce NULL for entity_id.
_NEW_FUNCTION = """
CREATE OR REPLACE FUNCTION audit.log_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
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
        BEGIN
            v_tenant_id := COALESCE(NEW.tenant_id, OLD.tenant_id);
        EXCEPTION
            WHEN undefined_column THEN
                v_tenant_id := NULL;
        END;

        -- Safely extract entity_id.
        -- Fallback chain: id -> tenant_id -> article_id -> corpus_id ->
        --                 submission_id -> session_id -> message_id ->
        --                 chunk_id -> 'unknown_<table>'
        BEGIN
            v_entity_id := COALESCE(NEW.id, OLD.id)::text;
        EXCEPTION
            WHEN undefined_column THEN
                BEGIN
                    v_entity_id := COALESCE(NEW.tenant_id, OLD.tenant_id)::text;
                EXCEPTION
                    WHEN undefined_column THEN
                        BEGIN
                            v_entity_id := COALESCE(NEW.article_id, OLD.article_id)::text;
                        EXCEPTION
                            WHEN undefined_column THEN
                                BEGIN
                                    v_entity_id := COALESCE(NEW.corpus_id, OLD.corpus_id)::text;
                                EXCEPTION
                                    WHEN undefined_column THEN
                                        BEGIN
                                            v_entity_id := COALESCE(NEW.submission_id, OLD.submission_id)::text;
                                        EXCEPTION
                                            WHEN undefined_column THEN
                                                BEGIN
                                                    v_entity_id := COALESCE(NEW.session_id, OLD.session_id)::text;
                                                EXCEPTION
                                                    WHEN undefined_column THEN
                                                        BEGIN
                                                            v_entity_id := COALESCE(NEW.message_id, OLD.message_id)::text;
                                                        EXCEPTION
                                                            WHEN undefined_column THEN
                                                                BEGIN
                                                                    v_entity_id := COALESCE(NEW.chunk_id, OLD.chunk_id)::text;
                                                                EXCEPTION
                                                                    WHEN undefined_column THEN
                                                                        v_entity_id := 'unknown_' || TG_TABLE_NAME;
                                                                END;
                                                        END;
                                                END;
                                        END;
                                END;
                        END;
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
$$;
"""

_OLD_FUNCTION = """
CREATE OR REPLACE FUNCTION audit.log_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
    DECLARE
        v_user_id uuid;
        v_actor_type text;
        v_tenant_id uuid;
        v_entity_id text;
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

        INSERT INTO audit.event (
            tenant_id, user_id, actor_type, entity_name, entity_id, action,
            old_values, new_values, occurred_at
        ) VALUES (
            v_tenant_id, v_user_id, v_actor_type, TG_TABLE_NAME::text, v_entity_id, TG_OP,
            CASE WHEN TG_OP IN ('DELETE', 'UPDATE') THEN row_to_json(OLD)::jsonb ELSE NULL END,
            CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb ELSE NULL END,
            NOW()
        );

        RETURN COALESCE(NEW, OLD);
    END;
$$;
"""


def upgrade() -> None:
    op.execute(_NEW_FUNCTION)


def downgrade() -> None:
    op.execute(_OLD_FUNCTION)
