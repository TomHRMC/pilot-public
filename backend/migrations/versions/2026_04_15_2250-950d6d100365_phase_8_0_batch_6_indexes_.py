"""phase_8_0_batch_6_indexes_communications_integrations_ai

Revision ID: 950d6d100365
Revises: 1fed134c8d51
Create Date: 2026-04-15 22:50:12.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "950d6d100365"
down_revision: str | None = "1fed134c8d51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- notification_type ---
    op.create_index(
        "ix_notification_type_tenant_id", "notification_type", ["tenant_id"]
    )

    # --- notification_template ---
    op.create_index(
        "ix_notification_template_tenant_id", "notification_template", ["tenant_id"]
    )
    op.create_index(
        "ix_notification_template_notification_type_code",
        "notification_template",
        ["notification_type_code"],
    )

    # --- notification_event ---
    op.create_index(
        "ix_notification_event_tenant_id", "notification_event", ["tenant_id"]
    )
    op.create_index(
        "ix_notification_event_notification_type_code",
        "notification_event",
        ["notification_type_code"],
    )
    op.create_index(
        "ix_notification_event_entity_type_code",
        "notification_event",
        ["entity_type_code"],
    )

    # --- notification_outbox ---
    op.create_index(
        "ix_notification_outbox_notification_event_id",
        "notification_outbox",
        ["notification_event_id"],
    )
    op.create_index(
        "ix_notification_outbox_contact_endpoint_id",
        "notification_outbox",
        ["contact_endpoint_id"],
    )
    op.create_index(
        "ix_notification_outbox_user_endpoint_id",
        "notification_outbox",
        ["user_endpoint_id"],
    )
    op.create_index(
        "ix_notification_outbox_recipient_contact_id",
        "notification_outbox",
        ["recipient_contact_id"],
    )
    op.create_index(
        "ix_notification_outbox_recipient_user_id",
        "notification_outbox",
        ["recipient_user_id"],
    )

    # --- notification_delivery_attempt ---
    op.create_index(
        "ix_notification_delivery_attempt_tenant_id",
        "notification_delivery_attempt",
        ["tenant_id"],
    )

    # --- tenant_user_notification_pref ---
    op.create_index(
        "ix_tenant_user_notification_pref_user_id",
        "tenant_user_notification_pref",
        ["user_id"],
    )

    # --- webhook_event ---
    op.create_index(
        "ix_webhook_event_event_type_code", "webhook_event", ["event_type_code"]
    )

    # --- webhook_delivery_attempt ---
    op.create_index(
        "ix_webhook_delivery_attempt_webhook_endpoint_id",
        "webhook_delivery_attempt",
        ["webhook_endpoint_id"],
    )

    # --- integration_credential ---
    op.create_index(
        "ix_integration_credential_initiated_by_user_id",
        "integration_credential",
        ["initiated_by_user_id"],
    )

    # --- integration_sync_mapping ---
    op.create_index(
        "ix_integration_sync_mapping_tenant_id",
        "integration_sync_mapping",
        ["tenant_id"],
    )

    # --- integration_sync_conflict ---
    op.create_index(
        "ix_integration_sync_conflict_app_service_id",
        "integration_sync_conflict",
        ["app_service_id"],
    )
    op.create_index(
        "ix_integration_sync_conflict_entity_type_code",
        "integration_sync_conflict",
        ["entity_type_code"],
    )
    op.create_index(
        "ix_integration_sync_conflict_resolved_by",
        "integration_sync_conflict",
        ["resolved_by"],
    )

    # --- integration_sync_log ---
    op.create_index(
        "ix_integration_sync_log_app_service_id",
        "integration_sync_log",
        ["app_service_id"],
    )

    # --- conversation_session ---
    op.create_index(
        "ix_conversation_session_user_id", "conversation_session", ["user_id"]
    )

    # --- voice_command_log ---
    op.create_index("ix_voice_command_log_user_id", "voice_command_log", ["user_id"])
    op.create_index(
        "ix_voice_command_log_message_id", "voice_command_log", ["message_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_notification_type_tenant_id", table_name="notification_type")
    op.drop_index(
        "ix_notification_template_tenant_id", table_name="notification_template"
    )
    op.drop_index(
        "ix_notification_template_notification_type_code",
        table_name="notification_template",
    )
    op.drop_index("ix_notification_event_tenant_id", table_name="notification_event")
    op.drop_index(
        "ix_notification_event_notification_type_code", table_name="notification_event"
    )
    op.drop_index(
        "ix_notification_event_entity_type_code", table_name="notification_event"
    )
    op.drop_index(
        "ix_notification_outbox_notification_event_id", table_name="notification_outbox"
    )
    op.drop_index(
        "ix_notification_outbox_contact_endpoint_id", table_name="notification_outbox"
    )
    op.drop_index(
        "ix_notification_outbox_user_endpoint_id", table_name="notification_outbox"
    )
    op.drop_index(
        "ix_notification_outbox_recipient_contact_id", table_name="notification_outbox"
    )
    op.drop_index(
        "ix_notification_outbox_recipient_user_id", table_name="notification_outbox"
    )
    op.drop_index(
        "ix_notification_delivery_attempt_tenant_id",
        table_name="notification_delivery_attempt",
    )
    op.drop_index(
        "ix_tenant_user_notification_pref_user_id",
        table_name="tenant_user_notification_pref",
    )
    op.drop_index("ix_webhook_event_event_type_code", table_name="webhook_event")
    op.drop_index(
        "ix_webhook_delivery_attempt_webhook_endpoint_id",
        table_name="webhook_delivery_attempt",
    )
    op.drop_index(
        "ix_integration_credential_initiated_by_user_id",
        table_name="integration_credential",
    )
    op.drop_index(
        "ix_integration_sync_mapping_tenant_id", table_name="integration_sync_mapping"
    )
    op.drop_index(
        "ix_integration_sync_conflict_app_service_id",
        table_name="integration_sync_conflict",
    )
    op.drop_index(
        "ix_integration_sync_conflict_entity_type_code",
        table_name="integration_sync_conflict",
    )
    op.drop_index(
        "ix_integration_sync_conflict_resolved_by",
        table_name="integration_sync_conflict",
    )
    op.drop_index(
        "ix_integration_sync_log_app_service_id", table_name="integration_sync_log"
    )
    op.drop_index("ix_conversation_session_user_id", table_name="conversation_session")
    op.drop_index("ix_voice_command_log_user_id", table_name="voice_command_log")
    op.drop_index("ix_voice_command_log_message_id", table_name="voice_command_log")
