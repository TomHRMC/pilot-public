/**
 * Photo — WatermelonDB model for offline job_attachment (photo) capture
 *
 * Location: apps/mobile/database/models/Photo.ts
 *
 * Photos use a SEPARATE S3 multipart upload pipeline (NOT the sync orchestrator
 * push loop). See database/sync/photo-upload.ts.
 *
 * sync_status for photos tracks S3 upload state, not entity sync state:
 *   'pending'  → queued; waiting for connectivity (or WiFi if wifi-only pref set)
 *   'syncing'  → S3 multipart upload in progress
 *   'synced'   → all chunks uploaded; complete-upload endpoint confirmed
 *   'failed'   → upload failed; resume from last chunk on retry
 *   'conflict' → not applicable for photos (no conflict class)
 *
 * Per batch-fe-b7-design.md Section A.2.2 and §15.5 S3 multipart upload.
 */

import { field } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class Photo extends SyncableModel {
  static table = "photos";

  @field("job_id") declare jobId: string;

  /** Optional: if this photo is attached to a specific expense */
  @field("expense_id") declare expenseId: string | null;

  /** Local device URI (file:// path); not uploaded — S3 upload uses this path */
  @field("local_uri") declare localUri: string;

  /** MIME type (image/jpeg, image/png, etc.) */
  @field("mime_type") declare mimeType: string;

  @field("file_size_bytes") declare fileSizeBytes: number;

  /** Populated after successful S3 upload completes; backend-assigned photo ID */
  @field("pilot_photo_id") declare pilotPhotoId: string | null;

  /** Upload progress percentage (0–100) for UI display */
  @field("upload_progress") declare uploadProgress: number;

  /** S3 multipart upload session ID; used for resumable uploads */
  @field("s3_session_id") declare s3SessionId: string | null;

  /** Index of the last successfully uploaded chunk; resume from chunk+1 on failure */
  @field("last_completed_chunk") declare lastCompletedChunk: number;

  /** Whether upload is held pending WiFi (from photo_upload_wifi_only preference) */
  @field("wifi_pending") declare wifiPending: boolean;
}
