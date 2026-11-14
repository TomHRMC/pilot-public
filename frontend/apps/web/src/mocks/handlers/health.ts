/**
 * MSW handler — GET /api/v1/health/celery
 *
 * Location: apps/web/src/mocks/handlers/health.ts
 *
 * Returns a mocked healthy Celery response for dev and test use.
 * Shape matches CeleryHealthResponse from packages/shared-api/src/health.ts
 */

import { http, HttpResponse } from "msw";

export const healthHandlers = [
  http.get("*/api/v1/health/celery", () => {
    return HttpResponse.json({
      status: "healthy",
      workers_active: 2,
      broker_connected: true,
      scheduled_tasks: 14,
      timestamp: new Date().toISOString(),
    });
  }),
];
