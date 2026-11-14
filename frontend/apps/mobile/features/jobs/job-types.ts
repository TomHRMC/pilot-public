/**
 * Job types for the Jobs tab (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/job-types.ts
 *
 * Mirrors components["schemas"]["JobListItem"] from api-schema.d.ts.
 * The @pilot/shared-types package index exports schema.d.ts (the older
 * generated schema); JobListItem was added to api-schema.d.ts by MOB-B1-BE.
 * Until the shared-types index is updated to also export api-schema, this
 * local type serves as the canonical source for mobile job list types.
 *
 * Shape confirmed against api-schema.d.ts §JobListItem.
 */

export interface JobListItem {
  /** UUID */
  id: string;
  /** UUID */
  tenant_id: string;
  /** UUID */
  customer_id: string;
  /** UUID */
  site_id: string;
  /** UUID */
  status_id: string;
  /** Human-readable status code e.g. "scheduled", "in_progress", "completed" */
  status_code?: string | null;
  /** Customer display_name from JOIN */
  customer_name?: string | null;
  /** ISO 8601 datetime */
  scheduled_start_at?: string | null;
  /** ISO 8601 datetime */
  scheduled_end_at?: string | null;
  /** Integer minutes */
  estimated_duration_minutes?: number | null;
  /** UUID of the recurrence rule — non-null when this job is part of a recurring series (MOB-B9) */
  recurrence_rule_id?: string | null;
}
