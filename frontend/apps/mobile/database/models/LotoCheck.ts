/**
 * LotoCheck — WatermelonDB model for offline LOTO (Lock Out Tag Out) safety check
 *
 * Location: apps/mobile/database/models/LotoCheck.ts
 *
 * LOTO checks are safety-critical operations that must be captured offline
 * and synced at the earliest opportunity. idempotency_key is critical here
 * to prevent duplicate safety records.
 *
 * Per batch-fe-b7-design.md Section A.2.2 and §15.2 offline contract.
 */

import { field, date } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class LotoCheck extends SyncableModel {
  static table = "loto_checks";

  @field("job_id") declare jobId: string;

  /**
   * LOTO check type — e.g., 'lockout_applied', 'voltage_verified',
   * 'energy_isolated', 'equipment_tested'
   */
  @field("check_type") declare checkType: string;

  @date("confirmed_at") declare confirmedAt: Date;

  /** GPS coordinates at time of LOTO confirmation */
  @field("gps_lat") declare gpsLat: number | null;
  @field("gps_lng") declare gpsLng: number | null;
}
