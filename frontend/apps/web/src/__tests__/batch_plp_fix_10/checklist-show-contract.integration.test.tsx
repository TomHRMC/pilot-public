/**
 * PLP-FIX-10 Integration — Checklist Show contract (INV-BUG-14)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_10/checklist-show-contract.integration.test.tsx
 *
 * Locks the Part A contract: clicking Show on the hidden pill fires PUT
 * {hidden: false}, and on refetch returning checklist_hidden: false the
 * widget stays expanded (the full checklist renders, not the pill).
 *
 * The FE was already correct (optimistic expand); Part A fixed the BE
 * one-way write. This test ensures the contract holds end-to-end via MSW.
 *
 * The widget is prop-driven (checklistState passed in), so we use a wrapper
 * that calls useOnboardingChecklist — mirroring the dashboard page pattern.
 * The optimistic mutation updates the query cache → wrapper re-renders →
 * widget receives updated checklistState.
 */

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
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { OnboardingChecklistWidget } from "@/features/onboarding/components/OnboardingChecklistWidget";
import { useOnboardingChecklist } from "@/features/onboarding/hooks/useOnboardingChecklist";
import type { OnboardingChecklistResponse } from "@/features/onboarding/types";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href }, children),
}));

// ── MSW server ───────────────────────────────────────────────────────────────

const TENANT_ID = "tenant-checklist-contract";

// Mutable checklist state — the GET handler reads from this, the PUT handler
// updates it, simulating the Part A backend fix (hidden=false persists).
let checklistHidden = true;

const baseResponse: OnboardingChecklistResponse = {
  tenant_id: TENANT_ID,
  account_created: true,
  legal_accepted: true,
  tier_selected: true,
  first_customer_added: false,
  first_customer_added_at: null,
  catalog_setup: false,
  catalog_setup_at: null,
  messaging_setup: false,
  quickbooks_connected: false,
  quickbooks_skipped: false,
  calendar_connected: false,
  calendar_skipped: false,
  team_invited: false,
  team_skipped: false,
  checklist_hidden: true,
  checklist_dismissed_permanently: false,
};

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  checklistHidden = true; // reset for next test
});
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAuth(role: PilotRole): AuthContextValue {
  const perms = Array.from(ROLE_PERMISSION_MAP[role]) as string[];
  return {
    user: {
      id: "u1",
      email: `${role}@pilot-dev.example.com`,
      role,
      tenantId: TENANT_ID,
      displayName: role,
      accessToken: "tok",
      permissions: perms,
    },
    isAuthenticated: true,
    role,
    permissions: perms,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
    whenSessionReady: vi.fn(),
  };
}

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

/**
 * Wrapper that mirrors the dashboard page pattern: fetches checklist state
 * via useOnboardingChecklist and passes it to the widget. This allows the
 * optimistic mutation (which updates the query cache) to flow through to
 * the widget via re-render.
 */
function ChecklistWrapper() {
  const { data: checklistState } = useOnboardingChecklist(TENANT_ID);
  if (!checklistState) return null;
  return (
    <OnboardingChecklistWidget
      tenantId={TENANT_ID}
      checklistState={checklistState}
    />
  );
}

function renderWithAuth(role: PilotRole) {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>
        <ChecklistWrapper />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-10 — checklist Show contract (INV-BUG-14)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("hidden pill → click Show → PUT {hidden: false} fires → refetch returns hidden=false → widget stays expanded", async () => {
    // Track PUT requests
    let putRequestBody: { hidden: boolean } | null = null;
    let putCallCount = 0;

    server.use(
      http.get("*/api/v1/tenants/:tenantId/onboarding/checklist", () => {
        return HttpResponse.json({
          ...baseResponse,
          checklist_hidden: checklistHidden,
        });
      }),
      http.put(
        "*/api/v1/tenants/:tenantId/onboarding/checklist/hidden",
        async ({ request }) => {
          putRequestBody = (await request.json()) as { hidden: boolean };
          putCallCount++;
          // Part A fix: persist the hidden=false (the BE now honors it)
          checklistHidden = putRequestBody.hidden;
          return HttpResponse.json({
            checklist_hidden: putRequestBody.hidden,
          });
        },
      ),
    );

    renderWithAuth("owner");

    // The hidden pill should render with a Show button
    await waitFor(() => {
      expect(screen.getByTestId("checklist-widget-pill")).toBeInTheDocument();
    });
    const showButton = screen.getByTestId("checklist-show-button");
    expect(showButton).toBeInTheDocument();

    // Click Show
    fireEvent.click(showButton);

    // The PUT should fire with {hidden: false}
    await waitFor(() => {
      expect(putCallCount).toBeGreaterThanOrEqual(1);
    });
    expect(putRequestBody).toEqual({ hidden: false });

    // After the mutation settles and the refetch returns checklist_hidden: false,
    // the widget should stay expanded (the full checklist renders, not the pill).
    // The optimistic update sets checklistHidden=false immediately, and the
    // refetch confirms it. The full widget (checklist-widget) should appear.
    await waitFor(() => {
      expect(
        screen.queryByTestId("checklist-widget-pill"),
      ).not.toBeInTheDocument();
    });

    // The expanded widget should be present
    await waitFor(() => {
      expect(screen.getByTestId("checklist-widget")).toBeInTheDocument();
    });
  });
});
