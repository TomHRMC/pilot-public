/**
 * ChangeOrder — WatermelonDB model for offline change_order capture
 *
 * Location: apps/mobile/database/models/ChangeOrder.ts
 *
 * Mirrors minimum fields from `change_order` backend table.
 * Per batch-fe-b7-design.md Section A.2.2.
 */

import { field } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class ChangeOrder extends SyncableModel {
  static table = "change_orders";

  @field("job_id") declare jobId: string;

  @field("title") declare title: string;

  @field("description") declare description: string | null;

  /** Total amount in cents */
  @field("total_amount_cents") declare totalAmountCents: number;

  /**
   * Change order status at capture time.
   * Backend allowed values: 'draft' | 'pending_approval' | 'approved' | 'rejected'
   */
  @field("status") declare status: string;
}
