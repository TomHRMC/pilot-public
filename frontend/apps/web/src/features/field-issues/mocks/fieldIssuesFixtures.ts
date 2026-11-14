/**
 * Field Issues fixtures — typed test data for MSW handlers and unit tests
 *
 * Location: apps/web/src/features/field-issues/mocks/fieldIssuesFixtures.ts
 *
 * Established FE-B9. Consumed by:
 *   - apps/web/src/mocks/handlers/fieldIssuesHandlers.ts
 *   - apps/web/__tests__/batch_fe_b9/ integration tests
 *
 * All fixture IDs are stable and cross-referenced in handler logic.
 */

import type {
  FieldIssueQueueItem,
  FieldIssueDetail,
  FieldIssueDiff,
} from "../types";

// ─── Common FieldIssueDiff entries ────────────────────────────────────────────

const timeEntryFieldDiffs: FieldIssueDiff[] = [
  {
    fieldName: "duration_minutes",
    techValue: 120,
    serverValue: 90,
    changeType: "modified",
    techChange: "modified",
    serverChange: "modified",
  },
  {
    fieldName: "notes",
    techValue: "Replaced panel breakers — extended due to GFCI work",
    serverValue: "Panel inspection",
    changeType: "modified",
    techChange: "modified",
    serverChange: "modified",
  },
  {
    fieldName: "labor_code",
    techValue: "ELEC-STD",
    serverValue: "ELEC-INSP",
    changeType: "modified",
    techChange: "modified",
    serverChange: "modified",
  },
];

const expenseFieldDiffs: FieldIssueDiff[] = [
  {
    fieldName: "amount_cents",
    techValue: 14750,
    serverValue: null,
    changeType: "added",
    techChange: "added",
    serverChange: "removed",
  },
  {
    fieldName: "vendor",
    techValue: "Home Depot Store 0231",
    serverValue: null,
    changeType: "added",
    techChange: "added",
    serverChange: "removed",
  },
];

// ─── Queue item fixtures (list endpoint) ──────────────────────────────────────

export const pendingTimeEntryIssue: FieldIssueQueueItem = {
  id: "fi-time-001",
  status: "pending",
  operationType: "time_entry",
  techId: "tech-jake-001",
  techName: "Jake Torres",
  capturedAt: "2026-05-25T14:30:00Z",
  escalatedAt: "2026-05-25T14:31:05Z",
  explainerSummary:
    "Time entry conflict: both tech and server modified duration_minutes",
  conflictType: "modified_modified",
};

export const pendingExpenseIssue: FieldIssueQueueItem = {
  id: "fi-expense-001",
  status: "pending",
  operationType: "expense",
  techId: "tech-rosa-002",
  techName: "Rosa Medina",
  capturedAt: "2026-05-25T11:15:00Z",
  escalatedAt: "2026-05-25T11:16:12Z",
  explainerSummary:
    "Expense deleted_modified: expense was deleted server-side while tech submitted it offline",
  conflictType: "deleted_modified",
};

export const permissionRevokedIssue: FieldIssueQueueItem = {
  id: "fi-perm-001",
  status: "pending",
  operationType: "time_entry",
  techId: "tech-chris-003",
  techName: "Chris Okafor",
  capturedAt: "2026-05-25T09:45:00Z",
  escalatedAt: "2026-05-25T09:46:30Z",
  explainerSummary:
    "Permission revoked: tech's session was revoked before offline capture could sync",
  conflictType: "modified_modified",
};

export const fieldIssueQueueList: FieldIssueQueueItem[] = [
  pendingTimeEntryIssue,
  pendingExpenseIssue,
  permissionRevokedIssue,
];

// ─── Detail fixtures (detail endpoint) ────────────────────────────────────────

/** time_entry modified_modified — standard two-column diff */
export const timeEntryModifiedModifiedDetail: FieldIssueDetail = {
  id: "fi-time-001",
  status: "pending",
  operationType: "time_entry",
  techId: "tech-jake-001",
  techName: "Jake Torres",
  techLastActiveAt: "2026-05-25T14:30:00Z",
  capturedAt: "2026-05-25T14:30:00Z",
  syncAttemptedAt: "2026-05-25T14:31:00Z",
  escalatedAt: "2026-05-25T14:31:05Z",
  explainerCopy:
    "Jake captured a time entry for 120 minutes while offline on Job #J-2201 (Panel Upgrade — Ruiz Residence). While offline, someone updated the same time entry on the server, changing the duration to 90 minutes. Both versions recorded different labor codes. You need to decide which version to keep.",
  techSnapshot: {
    duration_minutes: 120,
    notes: "Replaced panel breakers — extended due to GFCI work",
    labor_code: "ELEC-STD",
  },
  serverSnapshot: {
    duration_minutes: 90,
    notes: "Panel inspection",
    labor_code: "ELEC-INSP",
  },
  fieldDiffs: timeEntryFieldDiffs,
  conflictType: "modified_modified",
  resolution: null,
  resolvedByUserId: null,
  resolvedAt: null,
  expectedServerStateHash: "sha256-abc123def456",
};

/** expense deleted_modified — deletion conflict */
export const expenseDeletedModifiedDetail: FieldIssueDetail = {
  id: "fi-expense-001",
  status: "pending",
  operationType: "expense",
  techId: "tech-rosa-002",
  techName: "Rosa Medina",
  techLastActiveAt: "2026-05-25T11:14:00Z",
  capturedAt: "2026-05-25T11:15:00Z",
  syncAttemptedAt: "2026-05-25T11:16:00Z",
  escalatedAt: "2026-05-25T11:16:12Z",
  explainerCopy:
    "Rosa submitted an expense for $147.50 at Home Depot while offline on Job #J-2155. By the time her device reconnected, the expense record had been deleted from the server. You can restore Rosa's captured expense or discard it.",
  techSnapshot: {
    amount_cents: 14750,
    vendor: "Home Depot Store 0231",
    category: "Materials",
  },
  serverSnapshot: null,
  fieldDiffs: expenseFieldDiffs,
  conflictType: "deleted_modified",
  resolution: null,
  resolvedByUserId: null,
  resolvedAt: null,
  expectedServerStateHash: "sha256-del789ghi012",
};

/** time_entry permission_revoked — escalation context header variant */
export const permissionRevokedDetail: FieldIssueDetail = {
  id: "fi-perm-001",
  status: "pending",
  operationType: "time_entry",
  techId: "tech-chris-003",
  techName: "Chris Okafor",
  techLastActiveAt: "2026-05-25T09:00:00Z",
  capturedAt: "2026-05-25T09:45:00Z",
  syncAttemptedAt: "2026-05-25T09:46:00Z",
  escalatedAt: "2026-05-25T09:46:30Z",
  explainerCopy:
    "Chris captured a time entry offline, but their account permissions were updated before the data could sync. The system cannot automatically decide whether to apply Chris's captured data. Please review and determine whether Chris's time entry should be committed.",
  techSnapshot: {
    duration_minutes: 180,
    notes: "Full service call — circuit tracing",
    labor_code: "ELEC-SVC",
  },
  serverSnapshot: {
    duration_minutes: 0,
    notes: "",
    labor_code: null,
  },
  fieldDiffs: [
    {
      fieldName: "duration_minutes",
      techValue: 180,
      serverValue: 0,
      changeType: "modified",
      techChange: "modified",
      serverChange: "unchanged",
    },
  ],
  conflictType: "modified_modified",
  resolution: null,
  resolvedByUserId: null,
  resolvedAt: null,
  expectedServerStateHash: "sha256-perm345jkl678",
};

// ─── 409 response bodies ──────────────────────────────────────────────────────

/** 409 server_changed — opens StalenessRefreshDialog with refreshed diff */
export const fieldIssue409ServerChanged = {
  staleness_type: "server_changed" as const,
  refreshed_issue: {
    ...timeEntryModifiedModifiedDetail,
    fieldDiffs: [
      ...timeEntryFieldDiffs,
      {
        fieldName: "job_id",
        techValue: "job-2201",
        serverValue: "job-2201",
        changeType: "unchanged",
        techChange: "unchanged",
        serverChange: "unchanged",
      },
    ],
    explainerCopy:
      "Jake's time entry was updated again while you were viewing it. The server now shows 95 minutes (changed from 90). Please review the updated diff.",
    expectedServerStateHash: "sha256-refreshed-999",
  },
};

/** 409 auto_recovered — no dialog; success banner + navigate to queue */
export const fieldIssue409AutoRecovered = {
  staleness_type: "auto_recovered" as const,
  message:
    "This issue auto-recovered while you were viewing it. Jake's data has been committed automatically.",
};

/** 409 stale — no dialog; info banner + navigate to queue */
export const fieldIssue409Stale = {
  staleness_type: "stale" as const,
  message:
    "Jake discarded this captured data from their device. There's nothing to commit. Closing this issue.",
};

// ─── Summary fixture (mobile) ─────────────────────────────────────────────────

export const fieldIssuesSummaryFixture = {
  pending_count: 3,
};

export const fieldIssuesSummaryEmptyFixture = {
  pending_count: 0,
};
