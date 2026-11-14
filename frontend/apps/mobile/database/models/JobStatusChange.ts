/**
 * JobStatusChange — WatermelonDB model for offline job status transitions
 *
 * Location: apps/mobile/database/models/JobStatusChange.ts
 *
 * Captures job status changes made in the field before connectivity is restored.
 * Per batch-fe-b7-design.md Section A.2.2 and §15.2 offline contract.
 */

import { field, date } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class JobStatusChange extends SyncableModel {
  static table = "job_status_changes";

  @field("job_id") declare jobId: string;

  /**
   * Previous job status (e.g., 'scheduled', 'in_progress', 'on_hold')
   */
  @field("from_status") declare fromStatus: string;

  /**
   * New job status (e.g., 'in_progress', 'completed', 'on_hold')
   */
  @field("to_status") declare toStatus: string;

  @date("changed_at") declare changedAt: Date;

  @field("notes") declare notes: string | null;
}
