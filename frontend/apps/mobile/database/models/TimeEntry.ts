/**
 * TimeEntry — WatermelonDB model for offline job_time_entry capture
 *
 * Location: apps/mobile/database/models/TimeEntry.ts
 *
 * Mirrors minimum fields from `job_time_entry` backend table needed for
 * offline capture + sync push payload. WatermelonDB is a write buffer,
 * not a full relational mirror.
 *
 * Per batch-fe-b7-design.md Section A.2.2 and §15.2 offline contract.
 * Natural-key dedup on backend: (user_id, job_id, started_at).
 */

import { field, date } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class TimeEntry extends SyncableModel {
  static table = "time_entries";

  @field("job_id") declare jobId: string;
  @field("user_id") declare userId: string;

  @date("started_at") declare startedAt: Date;
  @date("ended_at") declare endedAt: Date | null;

  /** Decimal hours; computed from startedAt/endedAt but stored for offline display */
  @field("hours") declare hours: number | null;

  @field("notes") declare notes: string | null;

  /** GPS coordinates captured at check-in */
  @field("check_in_lat") declare checkInLat: number | null;
  @field("check_in_lng") declare checkInLng: number | null;

  /** Cents per hour at time of capture */
  @field("hourly_rate_cents") declare hourlyRateCents: number | null;

  /** Estimated remaining hours on the job */
  @field("hours_remaining_estimate") declare hoursRemainingEstimate:
    | number
    | null;

  /** Optional association to a specific quote line item */
  @field("quote_line_id") declare quoteLineId: string | null;
}
