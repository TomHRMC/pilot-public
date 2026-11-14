/**
 * EscalationStatusRow — Shared Types
 *
 * Location: packages/ui/src/escalation-status/types.ts
 *
 * Established in FE-B7. Consumed by FE-B9 (full owner escalation flow).
 * ⚠️ Interface locked — changes require FE-B9 impact review.
 *
 * Per batch-fe-b7-design.md Section F.3 and §16.11 Mobile-to-Web Escalation.
 */

export type EscalationStatus =
  | "pending" // Owner has not yet reviewed
  | "resolved" // Owner resolved; loop closed
  | "rejected"; // Owner rejected the escalation

export interface EscalationStatusRowProps {
  /** The entity type involved in the escalation */
  entityType:
    | "time_entry"
    | "expense"
    | "photo"
    | "change_order"
    | "loto_check"
    | "job_status_change"
    | "job_note"
    | "invoice_signoff";
  /** Human-readable summary of the conflicting entity */
  entitySummary: string;
  /** Current resolution status */
  status: EscalationStatus;
  /** ISO timestamp when escalation was created */
  escalatedAt: string;
  /**
   * Deep-link URL to the owner's web resolution surface.
   * FE-B7: stubbed as 'https://pilotfortrades.com/sync/escalations'
   * FE-B9: becomes 'pilot://sync/escalations/{escalationId}' universal link
   */
  webDeepLink: string;
  /** Resolution outcome message (when status === 'resolved' | 'rejected') */
  resolutionMessage?: string;
  /** Mobile testID */
  testID?: string;
}
