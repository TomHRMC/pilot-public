/**
 * PLP-FIX-9 Unit — PendingInvites layout (INV-BUG-6-rem)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_9/pending-invites-layout.test.tsx
 *
 * Asserts the actions column carries w-48 and the actions cell whitespace-nowrap
 * (class-level guard; pixel layout is Tom's prod check).
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
  beforeEach,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { PendingInvitesSection } from "@/features/settings/components/PendingInvitesSection";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/settings/team",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href }, children),
}));

// Mock the hooks directly — avoids apiClient token issues in test mode
vi.mock("@/features/settings/hooks/useTeamInvites", () => ({
  useTeamInvites: () => ({
    data: [
      {
        id: "inv-1",
        email: "verylongemailaddressthatmightoverflow@pilotfortrades.com",
        role_code: "technician",
        status: "pending",
        created_at: "2026-09-01T10:00:00Z",
        expires_at: "2026-09-15T10:00:00Z",
      },
    ],
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/features/settings/hooks/useResendInvite", () => ({
  useResendInvite: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/features/settings/hooks/useRevokeInvite", () => ({
  useRevokeInvite: () => ({ mutateAsync: vi.fn() }),
}));

// ── MSW ──────────────────────────────────────────────────────────────────────

const INVITES_FIXTURE = [
  {
    id: "inv-1",
    email: "verylongemailaddressthatmightoverflow@pilotfortrades.com",
    role_code: "technician",
    status: "pending",
    created_at: "2026-09-01T10:00:00Z",
    expires_at: "2026-09-15T10:00:00Z",
  },
];

const server = setupServer(
  http.get("*/api/v1/users/invites", () => HttpResponse.json(INVITES_FIXTURE)),
  http.get("*/api/v1/users", () => HttpResponse.json([])),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

const ownerAuth: AuthContextValue = {
  user: {
    id: "u1",
    email: "owner@pilot-dev.example.com",
    role: "owner",
    tenantId: "t1",
    displayName: "Owner",
    accessToken: "tok",
    permissions: ["*"],
  },
  isAuthenticated: true,
  role: "owner",
  permissions: ["*"],
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
  whenSessionReady: vi.fn(),
};

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-9 — PendingInvites layout (INV-BUG-6-rem)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("Actions column header has w-48 (not w-36)", async () => {
    render(
      <AuthContext.Provider value={ownerAuth}>
        <QueryClientProvider client={makeQC()}>
          <PendingInvitesSection />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Actions")).toBeInTheDocument();
    });

    const actionsHeader = screen.getByText("Actions");
    const th = actionsHeader.closest("th");
    expect(th?.className).toContain("w-48");
    expect(th?.className).not.toContain("w-36");
  });

  it("Actions cell has whitespace-nowrap", async () => {
    render(
      <AuthContext.Provider value={ownerAuth}>
        <QueryClientProvider client={makeQC()}>
          <PendingInvitesSection />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Actions")).toBeInTheDocument();
    });

    // Find the actions cell (last td in the invite row)
    const inviteRow = screen.getByTestId("invite-row-inv-1");
    const cells = inviteRow.querySelectorAll("td");
    const actionsCell = cells[cells.length - 1];
    expect(actionsCell?.className).toContain("whitespace-nowrap");
  });
});
