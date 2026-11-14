/**
 * JobNote — WatermelonDB model for offline job_notes capture
 *
 * Location: apps/mobile/database/models/JobNote.ts
 *
 * Mirrors minimum fields from `job_notes` backend table.
 * Natural-key dedup on backend: (created_by, job_id, created_at).
 * client_capture_at is used as the dedup timestamp.
 *
 * Per batch-fe-b7-design.md Section A.2.2 and §15.2 offline contract.
 */

import { field } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class JobNote extends SyncableModel {
  static table = "job_notes";

  @field("job_id") declare jobId: string;

  /** User ID of the note author */
  @field("created_by") declare createdBy: string;

  @field("content") declare content: string;

  /**
   * Optional note type for categorization.
   * e.g., 'field_observation', 'safety_note', 'material_note'
   */
  @field("note_type") declare noteType: string | null;
}
