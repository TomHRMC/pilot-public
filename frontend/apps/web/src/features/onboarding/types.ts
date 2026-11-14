/**
 * Onboarding Checklist — Types
 * Location: apps/web/src/features/onboarding/types.ts
 *
 * FE-B13: Post-wizard checklist widget and trial conversion types.
 */

export interface OnboardingChecklistState {
  tenantId: string;
  accountCreated: boolean;
  legalAccepted: boolean;
  tierSelected: boolean;
  firstCustomerAdded: boolean;
  firstCustomerAddedAt: string | null;
  catalogSetup: boolean;
  catalogSetupAt: string | null;
  // C-B5: Charter-only 10DLC messaging setup item
  messagingSetup: boolean;
  quickbooksConnected: boolean;
  quickbooksSkipped: boolean;
  calendarConnected: boolean;
  calendarSkipped: boolean;
  teamInvited: boolean;
  teamSkipped: boolean;
  checklistHidden: boolean;
  checklistDismissedPermanently: boolean;
}

/** Raw API response shape — snake_case from backend */
export interface OnboardingChecklistResponse {
  tenant_id: string;
  account_created: boolean;
  legal_accepted: boolean;
  tier_selected: boolean;
  first_customer_added: boolean;
  first_customer_added_at: string | null;
  catalog_setup: boolean;
  catalog_setup_at: string | null;
  // C-B5: Charter-only 10DLC messaging setup item
  messaging_setup: boolean;
  quickbooks_connected: boolean;
  quickbooks_skipped: boolean;
  calendar_connected: boolean;
  calendar_skipped: boolean;
  team_invited: boolean;
  team_skipped: boolean;
  checklist_hidden: boolean;
  checklist_dismissed_permanently: boolean;
}

export type SkippableChecklistItem = "quickbooks" | "calendar" | "team";

export interface ChecklistItemConfig {
  key: keyof OnboardingChecklistState;
  skippedKey?: keyof OnboardingChecklistState;
  label: string;
  description: string;
  actionLabel: string;
  actionRoute: string;
  isSkippable: boolean;
  isAutoComplete: boolean; // completed automatically by wizard (account, legal, tier)
}

/** Converts API snake_case response to camelCase state */
export function mapChecklistResponse(
  res: OnboardingChecklistResponse,
): OnboardingChecklistState {
  return {
    tenantId: res.tenant_id,
    accountCreated: res.account_created,
    legalAccepted: res.legal_accepted,
    tierSelected: res.tier_selected,
    firstCustomerAdded: res.first_customer_added,
    firstCustomerAddedAt: res.first_customer_added_at,
    catalogSetup: res.catalog_setup,
    catalogSetupAt: res.catalog_setup_at,
    messagingSetup: res.messaging_setup,
    quickbooksConnected: res.quickbooks_connected,
    quickbooksSkipped: res.quickbooks_skipped,
    calendarConnected: res.calendar_connected,
    calendarSkipped: res.calendar_skipped,
    teamInvited: res.team_invited,
    teamSkipped: res.team_skipped,
    checklistHidden: res.checklist_hidden,
    checklistDismissedPermanently: res.checklist_dismissed_permanently,
  };
}

/** Returns true if all checklist items are complete or skipped (widget should disappear) */
export function isChecklistComplete(state: OnboardingChecklistState): boolean {
  return (
    state.accountCreated &&
    state.legalAccepted &&
    state.tierSelected &&
    state.firstCustomerAdded &&
    state.catalogSetup &&
    state.messagingSetup &&
    (state.quickbooksConnected || state.quickbooksSkipped) &&
    (state.calendarConnected || state.calendarSkipped) &&
    (state.teamInvited || state.teamSkipped)
  );
}

/** All 8 checklist items in display order */
export const CHECKLIST_ITEMS: ChecklistItemConfig[] = [
  {
    key: "accountCreated",
    label: "Create your account",
    description: "Sign up for Pilot for Trades",
    actionLabel: "",
    actionRoute: "",
    isSkippable: false,
    isAutoComplete: true,
  },
  {
    key: "legalAccepted",
    label: "Accept agreements",
    description: "Review and accept Terms of Service and Privacy Policy",
    actionLabel: "",
    actionRoute: "",
    isSkippable: false,
    isAutoComplete: true,
  },
  {
    key: "tierSelected",
    label: "Choose your plan",
    description: "Select your subscription tier",
    actionLabel: "",
    actionRoute: "",
    isSkippable: false,
    isAutoComplete: true,
  },
  {
    key: "firstCustomerAdded",
    label: "Add your first customer",
    description: "Create your first customer record",
    actionLabel: "Add customer",
    actionRoute: "/customers?add=1",
    isSkippable: false,
    isAutoComplete: false,
  },
  {
    key: "catalogSetup",
    label: "Set up your service catalog",
    description: "Add your services and labor rates",
    actionLabel: "Set up catalog",
    actionRoute: "/catalog",
    isSkippable: false,
    isAutoComplete: false,
  },
  {
    key: "messagingSetup",
    label: "Set up text messaging",
    description: "Register your business for 10DLC SMS messaging",
    actionLabel: "Set up",
    actionRoute: "/settings/communications/sms-compliance",
    isSkippable: false,
    isAutoComplete: false,
  },
  {
    key: "quickbooksConnected",
    skippedKey: "quickbooksSkipped",
    label: "Connect QuickBooks",
    description: "Sync invoices and payments automatically",
    actionLabel: "Connect",
    actionRoute: "/settings/integrations/quickbooks",
    isSkippable: true,
    isAutoComplete: false,
  },
  {
    key: "calendarConnected",
    skippedKey: "calendarSkipped",
    label: "Connect your calendar",
    description: "Sync job schedules with Google Calendar",
    actionLabel: "Connect",
    actionRoute: "/settings/integrations/calendar",
    isSkippable: true,
    isAutoComplete: false,
  },
  {
    key: "teamInvited",
    skippedKey: "teamSkipped",
    label: "Invite your team",
    description: "Add technicians and office staff",
    actionLabel: "Invite",
    actionRoute: "/settings/team",
    isSkippable: true,
    isAutoComplete: false,
  },
];

/** Trial status types */
export interface TrialStatus {
  isOnTrial: boolean;
  daysRemaining: number;
  isExpired: boolean;
  showSoftGate: boolean; // 7d/3d/1d remaining
}
