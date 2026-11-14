/**
 * MSW handler — GET /api/v1/health/celery (mobile)
 *
 * Location: apps/mobile/mocks/handlers/health.ts
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
