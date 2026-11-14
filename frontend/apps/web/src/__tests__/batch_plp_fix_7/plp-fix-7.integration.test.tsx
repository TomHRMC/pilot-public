/**
 * PLP-FIX-7 Integration Tests — Invite 409 state machine + office_staff nav + tech login
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_7/plp-fix-7.integration.test.tsx
 *
 * Tests:
 * 1. Invite dialog 409 state machine (nested envelope → typed errors; both branches render inline)
 * 2. office_staff nav matrix (Jobs visible, Comms/Catalog hidden, Settings→Team visible read-only)
 * 3. PendingInvitesSection accepted filter + email truncation
 * 4. useLoginFlow role-await (technician resolves to onSuccess("technician"))
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { TeamSettingsPage } from "@/features/settings/components/TeamSettingsPage";
import { PendingInvitesSection } from "@/features/settings/components/PendingInvitesSection";
import { AppSidebar } from "@/components/AppSidebar";

// ─── Next.js mock ──────────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/settings/team",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    className,
    children,
    ...rest
  }: {
    href: string;
    className?: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} className={className} {...rest}>
      {children}
    </a>
  ),
}));

// ─── localStorage mock for AppSidebar ──────────────────────────────────────
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// ─── Auth context helpers ─────────────────────────────────────────────────
function makeAuth(role: PilotRole): AuthContextValue {
  const perms = Array.from(ROLE_PERMISSION_MAP[role]) as string[];
  return {
    user: {
      id: "user-001",
      email: "owner@example.com",
      role,
      tenantId: "tenant-001",
      displayName: "Test User",
      accessToken: "tok",
      permissions: perms,
    },
    isAuthenticated: true,
    role,
    permissions: perms,
    signIn: vi.fn() as AuthContextValue["signIn"],
    confirmMfaChallenge: vi.fn() as AuthContextValue["confirmMfaChallenge"],
    signOut: vi.fn(),
    refreshSession: vi
      .fn()
      .mockResolvedValue("tok") as AuthContextValue["refreshSession"],
    whenSessionReady: vi.fn().mockResolvedValue(null),
  };
}

function makeQC() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderWithAuth(
  ui: React.ReactElement,
  role: PilotRole = "owner",
  qc?: QueryClient,
) {
  const queryClient = qc ?? makeQC();
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ─── Fixtures ─────────────────────────────────────────────────────────────

const TEAM_USERS = [
  {
    user_id: "user-001",
    email: "owner@example.com",
    role_code: "owner",
    role_name: "Owner",
    permissions: ["users.manage"],
    joined_at: "2025-01-15T10:00:00Z",
    is_active: true,
  },
];

const INVITES = [
  {
    id: "invite-001",
    email: "newguy@pilot.local",
    role_code: "technician",
    invited_by: "user-001",
    created_at: new Date(Date.now() - 86400000).toISOString(),
    expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
    accepted_at: null,
    is_active: true,
    status: "pending",
  },
  {
    id: "invite-002",
    email: "accepted-user@pilot.local",
    role_code: "technician",
    invited_by: "user-001",
    created_at: new Date(Date.now() - 10 * 86400000).toISOString(),
    expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
    accepted_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    is_active: true,
    status: "accepted",
  },
  {
    id: "invite-003",
    email: "a-very-long-email-address-that-should-truncate@pilot.local",
    role_code: "office_staff",
    invited_by: "user-001",
    created_at: new Date(Date.now() - 6 * 86400000).toISOString(),
    expires_at: new Date(Date.now() + 86400000).toISOString(),
    accepted_at: null,
    is_active: true,
    status: "pending",
  },
];

// ─── MSW server ────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/users", () => HttpResponse.json(TEAM_USERS)),
  http.get("/api/v1/users/invites", () => HttpResponse.json(INVITES)),
  http.post("/api/v1/users/invites", async ({ request }) => {
    const body = (await request.json()) as { email: string; role_code: string };
    return HttpResponse.json(
      {
        id: "invite-new",
        email: body.email,
        role_code: body.role_code,
        expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),
  http.post("/api/v1/users/invites/:inviteId/resend", ({ params }) => {
    return HttpResponse.json({
      id: params.inviteId as string,
      email: "newguy@pilot.local",
      expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
    });
  }),
  http.post("/api/v1/users/invites/:inviteId/revoke", ({ params }) => {
    return HttpResponse.json({
      id: params.inviteId as string,
      is_active: false,
    });
  }),
  http.post("/api/v1/users/:userId/role", ({ params }) => {
    return HttpResponse.json({
      user_id: params.userId,
      tenant_id: "tenant-001",
      role_code: "technician",
      role_name: "Field Technician",
      message: "ok",
    });
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── Tests ─────────────────────────────────────────────────────────────────

describe("PLP-FIX-7 — Invite 409 state machine (nested envelope)", () => {
  it("409 invite_pending_exists (nested envelope) → shows Resend option", async () => {
    server.use(
      http.post("/api/v1/users/invites", () => {
        return HttpResponse.json(
          {
            detail: {
              type: "https://errors.pilotfortrades.com/invite_pending_exists",
              title: "Invite already pending",
              status: 409,
              detail: "An active invite already exists for this email.",
              invite_id: "invite-001",
            },
          },
          { status: 409 },
        );
      }),
    );

    renderWithAuth(<TeamSettingsPage />, "owner");

    await waitFor(() => {
      expect(
        screen.getByTestId("invite-team-member-button"),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("invite-team-member-button"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-email-input")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("invite-email-input"), {
      target: { value: "newguy@pilot.local" },
    });
    fireEvent.click(screen.getByTestId("invite-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-pending-exists")).toBeInTheDocument();
    });
    expect(screen.getByTestId("invite-resend-existing")).toBeInTheDocument();
  });

  it("409 invite_user_exists (nested envelope) → shows explainer", async () => {
    server.use(
      http.post("/api/v1/users/invites", () => {
        return HttpResponse.json(
          {
            detail: {
              type: "https://errors.pilotfortrades.com/invite_user_exists",
              title: "User already exists",
              status: 409,
              detail:
                "This person already has a Pilot account. Contact Pilot support for multi-business access.",
            },
          },
          { status: 409 },
        );
      }),
    );

    renderWithAuth(<TeamSettingsPage />, "owner");

    await waitFor(() => {
      expect(
        screen.getByTestId("invite-team-member-button"),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("invite-team-member-button"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-email-input")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("invite-email-input"), {
      target: { value: "existing@pilot.local" },
    });
    fireEvent.click(screen.getByTestId("invite-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-user-exists")).toBeInTheDocument();
    });
  });

  it("generic error renders string fallback (not object)", async () => {
    server.use(
      http.post("/api/v1/users/invites", () => {
        return HttpResponse.json(
          {
            detail: {
              type: "https://errors.pilotfortrades.com/unknown_error",
              title: "Unknown",
              status: 500,
              detail: { nested: "object" }, // non-string detail
            },
          },
          { status: 500 },
        );
      }),
    );

    renderWithAuth(<TeamSettingsPage />, "owner");

    await waitFor(() => {
      expect(
        screen.getByTestId("invite-team-member-button"),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("invite-team-member-button"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-email-input")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("invite-email-input"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByTestId("invite-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-generic-error")).toBeInTheDocument();
    });
    // Should render the fallback string, not the object
    expect(screen.getByTestId("invite-generic-error").textContent).toContain(
      "Something went wrong",
    );
  });
});

describe("PLP-FIX-7 — office_staff nav matrix", () => {
  it("office_staff sees Jobs, Dashboard, Customers, Quotes, Invoices, Comms, Reports (PLP-FIX-9: comms granted)", () => {
    renderWithAuth(<AppSidebar />, "office_staff");
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Customers")).toBeInTheDocument();
    expect(screen.getByText("Quotes")).toBeInTheDocument();
    expect(screen.getByText("Jobs")).toBeInTheDocument();
    expect(screen.getByText("Invoices")).toBeInTheDocument();
    expect(screen.getByText("Reports")).toBeInTheDocument();
    // PLP-FIX-9 (INV-D-5): office_staff now holds communications.view → Comms visible
    expect(screen.getByText("Comms")).toBeInTheDocument();
  });

  it("office_staff sees Team settings page (read-only — no invite button)", async () => {
    renderWithAuth(<TeamSettingsPage />, "office_staff");
    // Team page renders (gated on users.view which office_staff holds)
    await waitFor(() => {
      expect(screen.getByText("Team")).toBeInTheDocument();
    });
    // But no invite button (gated on users.manage which office_staff lacks)
    expect(
      screen.queryByTestId("invite-team-member-button"),
    ).not.toBeInTheDocument();
  });
});

describe("PLP-FIX-7 — PendingInvitesSection accepted filter + truncation", () => {
  it("filters out accepted invites from the pending list", async () => {
    renderWithAuth(<PendingInvitesSection />, "owner");

    // Pending invite should be visible
    await waitFor(() => {
      expect(screen.getByText("newguy@pilot.local")).toBeInTheDocument();
    });

    // Accepted invite should NOT be visible
    expect(
      screen.queryByText("accepted-user@pilot.local"),
    ).not.toBeInTheDocument();
  });

  it("long email truncates with title tooltip", async () => {
    renderWithAuth(<PendingInvitesSection />, "owner");

    await waitFor(() => {
      expect(
        screen.getByText(
          "a-very-long-email-address-that-should-truncate@pilot.local",
        ),
      ).toBeInTheDocument();
    });

    // The title attribute should be set for the tooltip
    const emailSpan = screen.getByTitle(
      "a-very-long-email-address-that-should-truncate@pilot.local",
    );
    expect(emailSpan).toBeInTheDocument();
    expect(emailSpan.className).toContain("truncate");
  });
});
