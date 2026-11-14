/**
 * Tenant Notification Defaults — Integration Tests (FE-UI-NAV-S1)
 *
 * Location: apps/web/src/__tests__/batch_fe_ui_nav_s1/tenant_notification_defaults.integration.test.tsx
 *
 * Tests that TenantNotificationDefaultsPage renders for owner role,
 * is hidden for tech role, and that reset action triggers DELETE mutation.
 *
 * Uses local setupServer (msw/node) following existing batch integration test pattern.
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { TenantNotificationDefaultsPage } from "@/features/settings/components/TenantNotificationDefaultsPage";
import { RoleGate } from "@pilot/ui/role-gate";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/notifications/tenant-defaults",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => React.createElement("a", { href, className }, children),
}));

// ─── MSW server ──────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/notifications/tenant-policy", () =>
    HttpResponse.json({
      policies: [
        { category_id: "job_activity", channel: "email", enabled: true },
        { category_id: "job_activity", channel: "push", enabled: false },
      ],
    }),
  ),
  http.delete("/api/v1/notifications/tenant-policy", () =>
    HttpResponse.json({ deleted_count: 2 }),
  ),
  // Categories endpoint for NotificationPreferenceMatrix
  http.get("/api/v1/notifications/categories", () =>
    HttpResponse.json({
      categories: [
        {
          category_id: "job_activity",
          display_label: "Job activity",
          description: "Updates on job status",
          display_order: 1,
          has_asymmetric_forced_minimum: false,
        },
      ],
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeAuth(
  role: "owner" | "accountant" | "office_staff" | "technician" = "owner",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "mike@example.com",
      role,
      tenantId: "t1",
      displayName: "Mike Johnson",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function renderPage(
  role: "owner" | "accountant" | "office_staff" | "technician" = "owner",
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AuthContext.Provider value={makeAuth(role)}>
        <RoleGate permission="settings.tenant.write">
          <TenantNotificationDefaultsPage />
        </RoleGate>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Tenant Notification Defaults Integration — FE-UI-NAV-S1", () => {
  it("renders page heading for owner role", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(
        screen.getByText(/team notification defaults/i),
      ).toBeInTheDocument();
    });
  });

  it("hides content for tech role (RoleGate hides-not-disables)", () => {
    renderPage("technician");
    // RoleGate hides the whole content — heading should not be present
    expect(
      screen.queryByText(/team notification defaults/i),
    ).not.toBeInTheDocument();
  });

  it("shows Reset action button for owner after loading", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /reset all to system defaults/i }),
      ).toBeInTheDocument();
    });
  });

  it("shows confirm/cancel buttons after clicking Reset", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /reset all to system defaults/i }),
      ).toBeInTheDocument();
    });
    fireEvent.click(
      screen.getByRole("button", { name: /reset all to system defaults/i }),
    );
    expect(
      screen.getByRole("button", { name: /confirm reset/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });

  it("cancel hides confirm dialog", async () => {
    renderPage("owner");
    await waitFor(() => {
      fireEvent.click(
        screen.getByRole("button", { name: /reset all to system defaults/i }),
      );
    });
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(
      screen.queryByRole("button", { name: /confirm reset/i }),
    ).not.toBeInTheDocument();
  });

  it("confirm reset triggers DELETE /api/v1/notifications/tenant-policy", async () => {
    const deleteSpy = vi.fn();
    server.use(
      http.delete("/api/v1/notifications/tenant-policy", () => {
        deleteSpy();
        return HttpResponse.json({ deleted_count: 2 });
      }),
    );

    renderPage("owner");
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /reset all to system defaults/i }),
      ).toBeInTheDocument();
    });
    fireEvent.click(
      screen.getByRole("button", { name: /reset all to system defaults/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /confirm reset/i }));

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledTimes(1);
    });
  });
});
