/**
 * MSW Sync Handlers — Mobile unit/integration test mocks
 *
 * Location: apps/mobile/mocks/handlers/sync.ts
 *
 * Provides mock responses for sync session and conflict endpoints.
 * Includes mock conflict payloads for all 4 severity classes.
 *
 * Per batch-fe-b7-design.md Section D.
 */

import { http, HttpResponse } from "msw";

const BASE_URL = "http://localhost:8000";

/** Mock conflict payloads for each severity class */
const MOCK_CONFLICTS = {
  auto_apply: {
    id: "conflict-auto-apply-001",
    entity_type: "time_entry",
    entity_summary: "Time entry for job JOB-001",
    severity_class: "auto_apply",
    local_version: { hours: 2.5, notes: "Local version" },
    server_version: { hours: 2.5, notes: "Server version" },
    field_diffs: [
      {
        field_name: "notes",
        label: "Notes",
        base_value: null,
        modified_value: "Server version",
        change_type: "added",
      },
    ],
    detected_at: new Date().toISOString(),
  },
  safe_to_apply: {
    id: "conflict-safe-001",
    entity_type: "expense",
    entity_summary: "Expense $45.00",
    severity_class: "safe_to_apply",
    local_version: { cost_cents: 4500, description: "Materials" },
    server_version: { cost_cents: 4500, description: "Materials - updated" },
    field_diffs: [
      {
        field_name: "description",
        label: "Description",
        base_value: "Materials",
        modified_value: "Materials - updated",
        change_type: "modified",
      },
    ],
    detected_at: new Date().toISOString(),
  },
  requires_review: {
    id: "conflict-review-001",
    entity_type: "change_order",
    entity_summary: "Change order: Panel upgrade",
    severity_class: "requires_review",
    local_version: { total_amount_cents: 150000, status: "pending_approval" },
    server_version: { total_amount_cents: 175000, status: "pending_approval" },
    field_diffs: [
      {
        field_name: "total_amount_cents",
        label: "Total Amount",
        base_value: 150000,
        modified_value: 175000,
        change_type: "modified",
      },
    ],
    detected_at: new Date().toISOString(),
  },
  escalate_to_owner: {
    id: "conflict-escalate-001",
    entity_type: "job_status_change",
    entity_summary: "Status: in_progress → completed",
    severity_class: "escalate_to_owner",
    local_version: { to_status: "completed" },
    server_version: { to_status: "on_hold" },
    field_diffs: [
      {
        field_name: "to_status",
        label: "New Status",
        base_value: "in_progress",
        modified_value: "completed",
        change_type: "modified",
      },
    ],
    detected_at: new Date().toISOString(),
  },
};

export const syncHandlers = [
  // POST /api/v1/mobile/sync-sessions — create a new sync session
  http.post(`${BASE_URL}/api/v1/mobile/sync-sessions`, () => {
    return HttpResponse.json({
      session_id: `session-${Date.now()}`,
      created_at: new Date().toISOString(),
    });
  }),

  // POST /api/v1/mobile/sync-sessions/:id/complete
  http.post(
    `${BASE_URL}/api/v1/mobile/sync-sessions/:sessionId/complete`,
    () => {
      return HttpResponse.json({
        status: "completed",
        completed_at: new Date().toISOString(),
      });
    },
  ),

  // GET /api/v1/mobile-sync/conflicts/:id — fetch conflict detail
  http.get(
    `${BASE_URL}/api/v1/mobile-sync/conflicts/:conflictId`,
    ({ params }) => {
      const { conflictId } = params;

      // Return conflict based on ID pattern
      if (String(conflictId).includes("auto-apply")) {
        return HttpResponse.json(MOCK_CONFLICTS.auto_apply);
      }
      if (String(conflictId).includes("safe")) {
        return HttpResponse.json(MOCK_CONFLICTS.safe_to_apply);
      }
      if (String(conflictId).includes("escalate")) {
        return HttpResponse.json(MOCK_CONFLICTS.escalate_to_owner);
      }

      // Default: requires_review
      return HttpResponse.json({
        ...MOCK_CONFLICTS.requires_review,
        id: conflictId,
      });
    },
  ),

  // POST /api/v1/mobile-sync/conflicts/:id/resolve
  http.post(
    `${BASE_URL}/api/v1/mobile-sync/conflicts/:conflictId/resolve`,
    () => {
      return HttpResponse.json({
        status: "resolved",
        resolved_at: new Date().toISOString(),
      });
    },
  ),

  // GET /api/v1/mobile-sync/state/:userId
  http.get(`${BASE_URL}/api/v1/mobile-sync/state/:userId`, () => {
    return HttpResponse.json({
      status: "idle",
      pending_count: 0,
      last_synced_at: new Date().toISOString(),
      resolved_conflicts: [],
      updates: [],
    });
  }),

  // POST /api/v1/mobile-sync/escalations
  http.post(`${BASE_URL}/api/v1/mobile-sync/escalations`, () => {
    return HttpResponse.json({
      escalation_id: `escalation-${Date.now()}`,
      status: "pending",
      created_at: new Date().toISOString(),
    });
  }),
];

export { MOCK_CONFLICTS };
