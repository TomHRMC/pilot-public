/**
 * Dev health page integration tests
 *
 * Location: apps/web/__tests__/batch_fe_b0/dev-health.integration.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

// MSW server for this test suite
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

// Mock @pilot/shared-api to use real checkApiHealth but with MSW intercepting
vi.mock("@pilot/shared-api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@pilot/shared-api")>();
  return actual;
});

describe("Dev health page", () => {
  it("renders the Dev Health Check heading", async () => {
    const DevHealthPage = (await import("@/app/(dev)/health/page")).default;
    render(<DevHealthPage />);
    expect(
      screen.getByRole("heading", { name: /dev health check/i }),
    ).toBeTruthy();
  });

  it("shows the route path info text", async () => {
    const DevHealthPage = (await import("@/app/(dev)/health/page")).default;
    render(<DevHealthPage />);
    expect(screen.getByText(/\/_dev\/health/)).toBeTruthy();
  });
});
