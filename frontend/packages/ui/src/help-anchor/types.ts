/**
 * HelpAnchor shared types — FE-B16
 *
 * Location: packages/ui/src/help-anchor/types.ts
 *
 * Cross-platform types for the contextual "?" help anchor.
 * 14 MVP surfaces consume HelpAnchor — interface is LOCKED after FE-B16.
 */

export type HelpActionType =
  | "viewed_quote"
  | "created_quote"
  | "accepted_quote"
  | "viewed_invoice"
  | "paid_invoice"
  | "assigned_job"
  | "completed_job"
  | "synced_calendar"
  | "viewed_qb_conflict"
  | "opened_settings"
  | "changed_setting"
  | "viewed_mfa"
  | "enrolled_mfa"
  | "viewed_field_issue"
  | "viewed_onboarding";

export interface HelpContextPayload {
  /** Current app route, e.g. '/settings/integrations/quickbooks' */
  route: string;
  /** Optional: identifies specific anchor on the surface */
  anchor_id?: string;
  /** Type of entity user is viewing — no entity contents (privacy rule) */
  entity_type?: string | null;
  /** Last 5 minutes of action types — client-side ephemeral */
  recent_actions: HelpActionType[];
  user_role: "owner" | "technician" | "office_staff" | "accountant";
  tenant_metadata: {
    size: "small" | "medium" | "large";
    trade: string;
  };
}

export interface HelpAnchorProps {
  /** The context payload to inject when this anchor opens help */
  contextPayload: HelpContextPayload;
  /** Accessible label for the "?" button (defaults to "Open contextual help") */
  label?: string;
  /** Size variant: 'sm' (14px icon, used inline) | 'md' (18px icon, used in cards) */
  size?: "sm" | "md";
  /** Optional additional className (web only) */
  className?: string;
  /** Optional testId */
  testId?: string;
}
