/**
 * WatermelonDB App Schema — Pilot Mobile
 *
 * Location: apps/mobile/database/schema.ts
 *
 * Defines all 7 offline entity tables plus the voice audio queue.
 * Each table includes the SyncableModel base fields plus entity-specific fields.
 *
 * IMPORTANT: Schema version must be incremented and a migration written
 * any time table definitions change (WatermelonDB requirement).
 *
 * Per batch-fe-b7-design.md Section A.2.1.
 * ⚠️ DO NOT use WatermelonDB built-in synchronize() — SyncOrchestrator handles all sync.
 */

import { appSchema, tableSchema } from "@nozbe/watermelondb";

/** Common sync-control columns present on every SyncableModel table */
const syncableColumns = [
  { name: "sync_status", type: "string" as const },
  { name: "idempotency_key", type: "string" as const, isIndexed: true },
  { name: "sync_error", type: "string" as const, isOptional: true },
  { name: "retry_count", type: "number" as const },
  { name: "client_capture_at", type: "number" as const, isIndexed: true },
  { name: "server_received_at", type: "number" as const, isOptional: true },
  { name: "created_at", type: "number" as const },
];

export const DATABASE_SCHEMA_VERSION = 3;

export const schema = appSchema({
  version: DATABASE_SCHEMA_VERSION,
  tables: [
    tableSchema({
      name: "time_entries",
      columns: [
        ...syncableColumns,
        { name: "job_id", type: "string", isIndexed: true },
        { name: "user_id", type: "string", isIndexed: true },
        { name: "started_at", type: "number" },
        { name: "ended_at", type: "number", isOptional: true },
        { name: "hours", type: "number", isOptional: true },
        { name: "notes", type: "string", isOptional: true },
        { name: "check_in_lat", type: "number", isOptional: true },
        { name: "check_in_lng", type: "number", isOptional: true },
        { name: "hourly_rate_cents", type: "number", isOptional: true },
        {
          name: "hours_remaining_estimate",
          type: "number",
          isOptional: true,
        },
        { name: "quote_line_id", type: "string", isOptional: true },
      ],
    }),

    tableSchema({
      name: "expenses",
      columns: [
        ...syncableColumns,
        { name: "job_id", type: "string", isIndexed: true },
        { name: "user_id", type: "string", isIndexed: true },
        { name: "job_expense_category_code", type: "string" },
        { name: "cost_cents", type: "number" },
        { name: "description", type: "string", isOptional: true },
        { name: "is_billable", type: "boolean" },
        { name: "incurred_at", type: "number" },
      ],
    }),

    tableSchema({
      name: "photos",
      columns: [
        ...syncableColumns,
        { name: "job_id", type: "string", isIndexed: true },
        { name: "expense_id", type: "string", isOptional: true },
        { name: "local_uri", type: "string" },
        { name: "mime_type", type: "string" },
        { name: "file_size_bytes", type: "number" },
        { name: "pilot_photo_id", type: "string", isOptional: true },
        { name: "upload_progress", type: "number" },
        { name: "s3_session_id", type: "string", isOptional: true },
        { name: "last_completed_chunk", type: "number" },
        { name: "wifi_pending", type: "boolean" },
      ],
    }),

    tableSchema({
      name: "change_orders",
      columns: [
        ...syncableColumns,
        { name: "job_id", type: "string", isIndexed: true },
        { name: "title", type: "string" },
        { name: "description", type: "string", isOptional: true },
        { name: "total_amount_cents", type: "number" },
        { name: "status", type: "string" },
      ],
    }),

    tableSchema({
      name: "loto_checks",
      columns: [
        ...syncableColumns,
        { name: "job_id", type: "string", isIndexed: true },
        { name: "check_type", type: "string" },
        { name: "confirmed_at", type: "number" },
        { name: "gps_lat", type: "number", isOptional: true },
        { name: "gps_lng", type: "number", isOptional: true },
      ],
    }),

    tableSchema({
      name: "job_status_changes",
      columns: [
        ...syncableColumns,
        { name: "job_id", type: "string", isIndexed: true },
        { name: "from_status", type: "string" },
        { name: "to_status", type: "string" },
        { name: "changed_at", type: "number" },
        { name: "notes", type: "string", isOptional: true },
      ],
    }),

    tableSchema({
      name: "job_notes",
      columns: [
        ...syncableColumns,
        { name: "job_id", type: "string", isIndexed: true },
        { name: "created_by", type: "string", isIndexed: true },
        { name: "content", type: "string" },
        { name: "note_type", type: "string", isOptional: true },
      ],
    }),

    tableSchema({
      name: "voice_audio_queue",
      columns: [
        ...syncableColumns,
        { name: "session_id", type: "string", isIndexed: true },
        { name: "audio_path", type: "string" },
        { name: "captured_at", type: "string" },
      ],
    }),

    // MOB-B4: NEC calculator offline storage
    tableSchema({
      name: "nec_calc_logs",
      columns: [
        ...syncableColumns,
        { name: "calc_type", type: "string" },
        { name: "inputs_json", type: "string" },
        { name: "result_json", type: "string" },
        { name: "nec_guide_version", type: "string" },
        { name: "is_offline_calc", type: "boolean" },
      ],
    }),

    // CE-1 Part B: Invoice sign-off offline capture
    tableSchema({
      name: "invoice_signoffs",
      columns: [
        ...syncableColumns,
        { name: "invoice_id", type: "string", isIndexed: true },
        { name: "signed_by_name", type: "string" },
        { name: "terms_acknowledged", type: "boolean" },
        { name: "signature_png_base64", type: "string" },
        { name: "captured_by", type: "string", isIndexed: true },
      ],
    }),
  ],
});
