/**
 * Expense — WatermelonDB model for offline job_expense capture
 *
 * Location: apps/mobile/database/models/Expense.ts
 *
 * Mirrors minimum fields from `job_expense` backend table.
 * Natural-key dedup index on backend: (user_id, job_id, incurred_at, cost_cents).
 *
 * Per batch-fe-b7-design.md Section A.2.2 and §15.2 offline contract.
 */

import { field, date } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class Expense extends SyncableModel {
  static table = "expenses";

  @field("job_id") declare jobId: string;
  @field("user_id") declare userId: string;

  /** Maps to job_expense_category_code on the backend */
  @field("job_expense_category_code") declare jobExpenseCategoryCode: string;

  /** Amount in cents */
  @field("cost_cents") declare costCents: number;

  @field("description") declare description: string | null;

  /** Whether this expense is billed to the customer */
  @field("is_billable") declare isBillable: boolean;

  @date("incurred_at") declare incurredAt: Date;
}
