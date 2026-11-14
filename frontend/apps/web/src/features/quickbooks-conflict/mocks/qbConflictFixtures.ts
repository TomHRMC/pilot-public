/**
 * QuickBooks Conflict fixtures — typed test data for MSW handlers and unit tests
 *
 * Location: apps/web/src/features/quickbooks-conflict/mocks/qbConflictFixtures.ts
 *
 * Established FE-B9. Consumed by:
 *   - apps/web/src/mocks/handlers/qbConflictHandlers.ts
 *   - apps/web/__tests__/batch_fe_b9/ integration tests
 *
 * One fixture per entity type; invoice has financial delta + tax period warning.
 * All fixture IDs stable and cross-referenced in handler logic.
 */

import type {
  QbConflictQueueItem,
  QbConflictDetail,
  QbFieldDiff,
} from "../types";

// ─── Shared field diffs ───────────────────────────────────────────────────────

const customerFieldDiffs: QbFieldDiff[] = [
  {
    fieldName: "display_name",
    pilot_value: "Ruiz Residence",
    external_value: "Ruiz, Maria",
    changeType: "modified",
  },
  {
    fieldName: "phone",
    pilot_value: "555-0142",
    external_value: "5550142",
    changeType: "modified",
  },
];

const quoteFieldDiffs: QbFieldDiff[] = [
  {
    fieldName: "total_amount_cents",
    pilot_value: 285000,
    external_value: 310000,
    changeType: "modified",
  },
  {
    fieldName: "line_items[0].description",
    pilot_value: "200A panel upgrade + GFCI protection",
    external_value: "200A panel upgrade",
    changeType: "modified",
  },
  {
    fieldName: "expiration_date",
    pilot_value: "2026-06-30",
    external_value: "2026-05-31",
    changeType: "modified",
  },
];

const invoiceFieldDiffs: QbFieldDiff[] = [
  {
    fieldName: "total_amount_cents",
    pilot_value: 285000,
    external_value: 322500,
    changeType: "modified",
  },
  {
    fieldName: "tax_amount_cents",
    pilot_value: 0,
    external_value: 37500,
    changeType: "modified",
  },
  {
    fieldName: "due_date",
    pilot_value: "2026-06-15",
    external_value: "2026-06-30",
    changeType: "modified",
  },
];

const expenseFieldDiffs: QbFieldDiff[] = [
  {
    fieldName: "amount_cents",
    pilot_value: 14750,
    external_value: 16200,
    changeType: "modified",
  },
  {
    fieldName: "account",
    pilot_value: "Materials - Electrical",
    external_value: "Job Expenses",
    changeType: "modified",
  },
];

// ─── Queue item fixtures ───────────────────────────────────────────────────────

export const customerConflictQueueItem: QbConflictQueueItem = {
  id: "qb-cust-001",
  entityType: "customer",
  entityId: "cust-ruiz-001",
  entityDisplayName: "Ruiz Residence",
  conflictType: "modified_modified",
  masterDirection: "pilot",
  pilotModifiedAt: "2026-05-25T10:00:00Z",
  externalModifiedAt: "2026-05-25T09:45:00Z",
  financialDeltaCents: null,
  resolution: null,
  detectedAt: "2026-05-25T10:05:00Z",
  daysUntilExpiry: null,
};

export const quoteConflictQueueItem: QbConflictQueueItem = {
  id: "qb-quote-001",
  entityType: "quote",
  entityId: "quote-2201",
  entityDisplayName: "Quote #Q-2201 — Panel Upgrade",
  conflictType: "modified_modified",
  masterDirection: "pilot",
  pilotModifiedAt: "2026-05-25T08:30:00Z",
  externalModifiedAt: "2026-05-25T08:15:00Z",
  financialDeltaCents: null,
  resolution: null,
  detectedAt: "2026-05-25T08:35:00Z",
  daysUntilExpiry: 5,
};

export const invoiceConflictQueueItem: QbConflictQueueItem = {
  id: "qb-invoice-001",
  entityType: "invoice",
  entityId: "inv-5501",
  entityDisplayName: "Invoice #INV-5501 — Ruiz Residence",
  conflictType: "modified_modified",
  masterDirection: "external", // QB is master for invoices (design doc Decision 3)
  pilotModifiedAt: "2026-05-24T15:00:00Z",
  externalModifiedAt: "2026-05-24T16:30:00Z",
  financialDeltaCents: 3750, // $37.50 delta — QB has tax
  resolution: null,
  detectedAt: "2026-05-24T16:35:00Z",
  daysUntilExpiry: null,
};

export const expenseConflictQueueItem: QbConflictQueueItem = {
  id: "qb-expense-001",
  entityType: "expense",
  entityId: "exp-881",
  entityDisplayName: "Expense — Home Depot Store 0231",
  conflictType: "modified_modified",
  masterDirection: "pilot",
  pilotModifiedAt: "2026-05-23T11:00:00Z",
  externalModifiedAt: "2026-05-23T10:45:00Z",
  financialDeltaCents: null,
  resolution: null,
  detectedAt: "2026-05-23T11:05:00Z",
  daysUntilExpiry: null,
};

export const qbConflictQueueList: QbConflictQueueItem[] = [
  invoiceConflictQueueItem, // Invoice sorted first (highest stakes)
  quoteConflictQueueItem,
  customerConflictQueueItem,
  expenseConflictQueueItem,
];

// ─── Detail fixtures ───────────────────────────────────────────────────────────

export const customerConflictDetail: QbConflictDetail = {
  id: "qb-cust-001",
  entityType: "customer",
  entityId: "cust-ruiz-001",
  entityDisplayName: "Ruiz Residence",
  conflictType: "modified_modified",
  masterDirection: "pilot",
  pilotModifiedAt: "2026-05-25T10:00:00Z",
  externalModifiedAt: "2026-05-25T09:45:00Z",
  pilotModifiedByUserId: "user-mike",
  pilotModifiedByName: "Mike Gonzalez",
  fieldDiffs: customerFieldDiffs,
  financialDeltaCents: null,
  pilotAmountCents: null,
  qbAmountCents: null,
  arImpactDescription: null,
  taxPeriodWarning: null,
  qbTransactionUrl: null,
  resolution: null,
  resolvedAt: null,
  autoResolvedStale: false,
};

export const quoteConflictDetail: QbConflictDetail = {
  id: "qb-quote-001",
  entityType: "quote",
  entityId: "quote-2201",
  entityDisplayName: "Quote #Q-2201 — Panel Upgrade",
  conflictType: "modified_modified",
  masterDirection: "pilot",
  pilotModifiedAt: "2026-05-25T08:30:00Z",
  externalModifiedAt: "2026-05-25T08:15:00Z",
  pilotModifiedByUserId: "user-mike",
  pilotModifiedByName: "Mike Gonzalez",
  fieldDiffs: quoteFieldDiffs,
  financialDeltaCents: null,
  pilotAmountCents: null,
  qbAmountCents: null,
  arImpactDescription: null,
  taxPeriodWarning: null,
  qbTransactionUrl: null,
  resolution: null,
  resolvedAt: null,
  autoResolvedStale: false,
};

/**
 * Invoice conflict detail — QB is master (masterDirection="external")
 * Includes: financialDeltaCents=3750, taxPeriodWarning="Q1 2026", qbTransactionUrl
 */
export const invoiceConflictDetail: QbConflictDetail = {
  id: "qb-invoice-001",
  entityType: "invoice",
  entityId: "inv-5501",
  entityDisplayName: "Invoice #INV-5501 — Ruiz Residence",
  conflictType: "modified_modified",
  masterDirection: "external", // QB is master — renders QB on left
  pilotModifiedAt: "2026-05-24T15:00:00Z",
  externalModifiedAt: "2026-05-24T16:30:00Z",
  pilotModifiedByUserId: "user-mike",
  pilotModifiedByName: "Mike Gonzalez",
  fieldDiffs: invoiceFieldDiffs,
  financialDeltaCents: 3750, // QB total is $37.50 higher (tax applied)
  pilotAmountCents: 285000, // $2,850.00
  qbAmountCents: 322500, // $3,225.00 (includes $375 tax)
  arImpactDescription:
    "QuickBooks version includes sales tax. Accepting Pilot's version will remove $375.00 from AR.",
  taxPeriodWarning: "Q1 2026", // Filed quarter — triggers amber banner
  qbTransactionUrl: "https://app.qbo.intuit.com/app/invoice?txnId=inv-5501-ext",
  resolution: null,
  resolvedAt: null,
  autoResolvedStale: false,
};

export const expenseConflictDetail: QbConflictDetail = {
  id: "qb-expense-001",
  entityType: "expense",
  entityId: "exp-881",
  entityDisplayName: "Expense — Home Depot Store 0231",
  conflictType: "modified_modified",
  masterDirection: "pilot",
  pilotModifiedAt: "2026-05-23T11:00:00Z",
  externalModifiedAt: "2026-05-23T10:45:00Z",
  pilotModifiedByUserId: "user-mike",
  pilotModifiedByName: "Mike Gonzalez",
  fieldDiffs: expenseFieldDiffs,
  financialDeltaCents: null,
  pilotAmountCents: null,
  qbAmountCents: null,
  arImpactDescription: null,
  taxPeriodWarning: null,
  qbTransactionUrl: null,
  resolution: null,
  resolvedAt: null,
  autoResolvedStale: false,
};

// ─── 409 response body ────────────────────────────────────────────────────────

/** 409 auto-recovery — no dialog; success toast + navigate to queue */
export const qbConflict409AutoRecovery = {
  staleness_type: "auto_recovered" as const,
  message:
    "This conflict resolved itself before you got to it. QuickBooks and Pilot are now in sync.",
};
