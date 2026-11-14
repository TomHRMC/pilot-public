/**
 * UI-FIX-2B MSW Handlers — Job Technician Assignments
 *
 * Location: apps/web/src/mocks/handlers/assignmentHandlers.ts
 *
 * Covers:
 *   GET    /api/v1/scheduling/jobs/:jobId/assignments
 *   POST   /api/v1/scheduling/jobs/:jobId/assignments
 *   DELETE /api/v1/scheduling/jobs/:jobId/assignments/:assignmentId
 *
 * Added by: UI-FIX-2B React Engineer
 */

import { http, HttpResponse } from "msw";

interface MockAssignment {
  id: string;
  job_id: string;
  user_id: string;
  role: "primary" | "helper";
  ordinal: number;
  assigned_at: string;
  is_active: boolean;
}

// Mutable in-memory store for assignment mock state
let mockAssignments: MockAssignment[] = [
  {
    id: "assign-001",
    job_id: "job-001",
    user_id: "user-002",
    role: "primary",
    ordinal: 1,
    assigned_at: "2026-07-21T10:00:00Z",
    is_active: true,
  },
];

let nextAssignId = 2;

export const assignmentHandlers = [
  // GET /api/v1/scheduling/jobs/:jobId/assignments
  http.get("/api/v1/scheduling/jobs/:jobId/assignments", ({ params }) => {
    const { jobId } = params as { jobId: string };
    const filtered = mockAssignments.filter(
      (a) => a.job_id === jobId && a.is_active,
    );
    return HttpResponse.json(filtered);
  }),

  // POST /api/v1/scheduling/jobs/:jobId/assignments
  http.post(
    "/api/v1/scheduling/jobs/:jobId/assignments",
    async ({ params, request }) => {
      const { jobId } = params as { jobId: string };
      const body = (await request.json()) as {
        user_id: string;
        role: "primary" | "helper";
        ordinal?: number;
      };
      const newAssignment = {
        id: `assign-${String(nextAssignId++).padStart(3, "0")}`,
        job_id: jobId,
        user_id: body.user_id,
        role: body.role,
        ordinal:
          body.ordinal ??
          mockAssignments.filter((a) => a.job_id === jobId).length + 1,
        assigned_at: new Date().toISOString(),
        is_active: true,
      };
      mockAssignments.push(newAssignment);
      return HttpResponse.json(newAssignment, { status: 201 });
    },
  ),

  // DELETE /api/v1/scheduling/jobs/:jobId/assignments/:assignmentId
  http.delete(
    "/api/v1/scheduling/jobs/:jobId/assignments/:assignmentId",
    ({ params }) => {
      const { assignmentId } = params as { assignmentId: string };
      const idx = mockAssignments.findIndex((a) => a.id === assignmentId);
      if (idx === -1) {
        return HttpResponse.json(
          { detail: "Assignment not found" },
          { status: 404 },
        );
      }
      mockAssignments.splice(idx, 1);
      return HttpResponse.json({}, { status: 200 });
    },
  ),
];

/** Reset mock state — call in test afterEach if needed */
export function resetAssignmentMocks() {
  mockAssignments = [
    {
      id: "assign-001",
      job_id: "job-001",
      user_id: "user-002",
      role: "primary",
      ordinal: 1,
      assigned_at: "2026-07-21T10:00:00Z",
      is_active: true,
    },
  ];
  nextAssignId = 2;
}
