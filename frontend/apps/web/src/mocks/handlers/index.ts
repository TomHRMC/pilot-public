/**
 * MSW handlers barrel — web
 *
 * Location: apps/web/src/mocks/handlers/index.ts
 *
 * Aggregates all domain handlers. New domain handler files are added here
 * as they are created in subsequent FE batches.
 */

import { healthHandlers } from "./health";
import { authHandlers } from "./auth";
import { scheduleHandlers } from "./schedule";
import { jobsHandlers } from "./jobs";
import { reportsHandlers } from "./reports";
import { calendarConflictHandlers } from "./calendarConflictHandlers";
import { fieldIssuesHandlers } from "./fieldIssuesHandlers";
import { qbConflictHandlers } from "./qbConflictHandlers";
// FE-B12 handlers
import { notificationPreferenceHandlers } from "./notificationPreferenceHandlers";
import { voicePersonaHandlers } from "./voicePersonaHandlers";
import { accountSecurityHandlers } from "./accountSecurityHandlers";
// FE-B13 handlers
import { signupHandlers } from "./signupHandlers";
import { onboardingHandlers } from "./onboardingHandlers";
// FE-B14 handlers
import { publicLinkHandlers } from "./publicLinkHandlers";
import { emailBrandingHandlers } from "./emailBrandingHandlers";
// FE-B16 handlers
import { helpHandlers } from "./helpHandlers";
// BETA-B3 handlers
import { quotesListHandlers } from "./quotesListHandlers";
// BETA-B4 handlers
import { betaB4Handlers } from "./betaB4Handlers";
// FE-B18 handlers
import { customerHandlers } from "./customerHandlers";
// FE-B19 handlers
import { quoteBuilderHandlers } from "./quoteBuilderHandlers";
// FE-B20 handlers
import { catalogHandlers } from "./catalogHandlers";
// FE-B22 handlers
import { invoiceDetailHandlers } from "./invoiceDetailHandlers";
// FE-B23 handlers
import { b23Handlers } from "./b23Handlers";
// DLC-1 handlers
import { dlcHandlers } from "./dlcHandlers";
// FE-B6 / FE-B10 communications handlers
import { communicationHandlers } from "./communications";
import { customerCommsHandlers } from "./customerCommsHandlers";
// MKT-B11-D handlers — dispatch board lane redesign
import { dispatchBoardHandlers } from "./dispatchBoardHandlers";
// FE-B31 handlers — recurring jobs
import { recurrenceRuleHandlers } from "./recurrenceRuleHandlers";
// UI-FIX-2F handlers — Stripe Connect payment method
import { stripeConnectHandlers } from "./stripeConnectHandlers";
// FE-UI-NAV-S1 handlers — avatar upload + tenant notification defaults
import { settingsNavHandlers } from "./settingsNavHandlers";
// UI-FIX-2B handlers — multi-tech job assignments
import { assignmentHandlers } from "./assignmentHandlers";
// BILLING-B1 handlers — payment schedules (9 endpoints)
import { paymentScheduleHandlers } from "./paymentScheduleHandlers";
// UP-1 handlers — WIP report
import { wipHandlers } from "./wipHandlers";
// C-B9 handlers — messaging provisioning (10DLC)
import { messagingProvisioningHandlers } from "./messagingProvisioningHandlers";
// C-B11 handlers — operator cohort dashboard
import { cohortDashboardHandlers } from "./cohortDashboardHandlers";
// C-B12 handlers — Charter upgrade forfeiture
import { charterUpgradeHandlers } from "./charterUpgradeHandlers";
// C-B15 handlers — operator tenants + impersonation
import { operatorTenantsHandlers } from "./operatorTenantsHandlers";
// CE-1 Part C handlers — invoice signoff + resolve variance
import { ce1SignoffHandlers } from "./ce1SignoffHandlers";
// C-B16 handlers — tenant site (hosted compliance + slug availability + publish)
import { tenantSiteHandlers } from "./tenantSiteHandlers";
// STRIPE-CONNECT-1-C handlers — billing payment-contact (GET + PATCH)
import { billingPaymentContactHandlers } from "./billingPaymentContactHandlers";
// TEAM-INVITE-1 handlers — invite CRUD + public landing lookup
import { teamInviteHandlers } from "./teamInviteHandlers";
// PLP-FIX-7 handlers — users/me/permissions (server-authoritative RBAC)
import { userPermissionsHandlers } from "./userPermissionsHandlers";

export const handlers = [
  ...healthHandlers,
  ...authHandlers,
  ...scheduleHandlers,
  ...jobsHandlers,
  ...reportsHandlers,
  ...calendarConflictHandlers,
  ...fieldIssuesHandlers,
  ...qbConflictHandlers,
  // FE-B12
  ...notificationPreferenceHandlers,
  ...voicePersonaHandlers,
  ...accountSecurityHandlers,
  // FE-B13
  ...signupHandlers,
  ...onboardingHandlers,
  // FE-B14
  ...publicLinkHandlers,
  ...emailBrandingHandlers,
  // FE-B16
  ...helpHandlers,
  // BETA-B3 — quotes list enhanced mock (status_code + customer_name until BE-3/BE-4 close)
  ...quotesListHandlers,
  // BETA-B4 — settings missing pages, MFA policy, team, billing, integrations
  ...betaB4Handlers,
  // FE-B18 — customer + site CRUD
  ...customerHandlers,
  // FE-B19 — quote builder: create, lines, submit-for-approval, public-link, convert
  ...quoteBuilderHandlers,
  // FE-B20 — catalog: pricebook, markups, labor rates, supplier items
  ...catalogHandlers,
  // FE-B22 — invoice detail, create, send, record-payment, AR aging
  ...invoiceDetailHandlers,
  // FE-B23 — dashboard BI, notifications, voice sessions
  ...b23Handlers,
  // DLC-1 — 10DLC profile GET/PUT
  ...dlcHandlers,
  // FE-B6 — comms template types, preview, send, customer history, recent aggregate
  ...communicationHandlers,
  // FE-B10 — SMS threads, unrouted messages, SSE streams
  ...customerCommsHandlers,
  // MKT-B11-D — subscription tiers with schedule_lanes, job PATCH for lane board
  ...dispatchBoardHandlers,
  // FE-B31 — recurrence rules CRUD
  ...recurrenceRuleHandlers,
  // UI-FIX-2F — Stripe Connect payment method
  ...stripeConnectHandlers,
  // FE-UI-NAV-S1 — avatar upload + tenant notification defaults (MSW stubs)
  ...settingsNavHandlers,
  // UI-FIX-2B — multi-tech job assignments GET/POST/DELETE
  ...assignmentHandlers,
  // BILLING-B1 — payment schedules (9 endpoints + 422/409 overrides)
  ...paymentScheduleHandlers,
  // UP-1 — WIP report
  ...wipHandlers,
  // C-B9 — messaging provisioning (10DLC)
  ...messagingProvisioningHandlers,
  // C-B11 — operator cohort dashboard (cohort overview, extend, close, auth/me)
  ...cohortDashboardHandlers,
  // C-B12 — Charter upgrade forfeiture (upgrade-from-charter + test twin)
  ...charterUpgradeHandlers,
  // C-B15 — operator tenants list + impersonation start/end
  ...operatorTenantsHandlers,
  // CE-1 Part C — invoice signoff GET + resolve-variance POST
  ...ce1SignoffHandlers,
  // C-B16 — tenant site config, slug availability, publish/unpublish, public snapshot
  ...tenantSiteHandlers,
  // STRIPE-CONNECT-1-C — billing payment-contact GET + PATCH
  ...billingPaymentContactHandlers,
  // TEAM-INVITE-1 — invite CRUD + public landing lookup
  ...teamInviteHandlers,
  // PLP-FIX-7 — users/me/permissions (server-authoritative RBAC fixtures)
  ...userPermissionsHandlers,
];
