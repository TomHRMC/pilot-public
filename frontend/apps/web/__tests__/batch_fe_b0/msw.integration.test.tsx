/**
 * MSW + apiClient integration tests
 *
 * Location: apps/web/__tests__/batch_fe_b0/msw.integration.test.tsx
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { apiClient } from "@pilot/shared-api";

const server = setupServer(
  http.get("*/api/v1/health/celery", () => {
    return HttpResponse.json({
      status: "healthy",
      workers_active: 2,
      broker_connected: true,
      scheduled_tasks: 14,
      timestamp: "2026-05-21T16:00:00.000Z",
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("MSW + apiClient integration", () => {
  it("health endpoint is intercepted by MSW handler and returns mocked response", async () => {
    const response = await apiClient.get("/api/v1/health/celery");
    expect(response.data.status).toBe("healthy");
    expect(response.data.workers_active).toBe(2);
    expect(response.data.broker_connected).toBe(true);
  });

  it("MSW returns correct scheduled_tasks count", async () => {
    const response = await apiClient.get("/api/v1/health/celery");
    expect(response.data.scheduled_tasks).toBe(14);
  });

  it("MSW handler can be overridden for specific test scenarios", async () => {
    server.use(
      http.get("*/api/v1/health/celery", () => {
        return HttpResponse.json({
          status: "unhealthy",
          workers_active: 0,
          broker_connected: false,
          scheduled_tasks: 0,
          timestamp: new Date().toISOString(),
        });
      }),
    );

    const response = await apiClient.get("/api/v1/health/celery");
    expect(response.data.status).toBe("unhealthy");
  });
});
