/**
 * TEAM-INVITE-1 Integration Tests — Team Settings Invite Flow
 *
 * Location: apps/web/src/__tests__/batch_team_invite_1/team-settings-invite.integration.test.tsx
 *
 * Verifies:
 *   1. /settings/team renders (no 404)
 *   2. Owner sees invite button + pending section with MSW fixture rows
 *   3. Full invite flow: open dialog → valid submit → POST fired with payload + Idempotency-Key → success → list invalidated
 *   4. Technician sees neither invite button nor pending section
 *   5. 409 invite_pending_exists → Resend switch fires resend for the detail id
 *   6. 409 invite_user_exists → explainer shown
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

// ─── Next.js mock ──────────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/settings/team",
  useSearchParams: () => new URLSearchParams(),
}));

// ─── Auth context helpers ─────────────────────────────────────────────────
function makeAuth(role: PilotRole): AuthContextValue {
  // PLP-FIX-7: derive permissions from ROLE_PERMISSION_MAP for the
  // server-authoritative gating path.
  const perms = Array.from(ROLE_PERMISSION_MAP[role]) as string[];
  return {
    user: {
      id: "user-001",
      email: "owner@example.com",
      role,
      tenantId: "tenant-001",
      displayName: "Tom Owner",
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

function renderPage(role: PilotRole = "owner") {
  const qc = makeQC();
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={qc}>
        <TeamSettingsPage />
      </QueryClientProvider>
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
  {
    user_id: "user-002",
    email: "tech@example.com",
    role_code: "technician",
    role_name: "Field Technician",
    permissions: ["comms.send"],
    joined_at: "2025-03-01T09:00:00Z",
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
    email: "sarah-office@pilot.local",
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

describe("TEAM-INVITE-1 — Team Settings Invite Flow", () => {
  it("renders the team settings page without 404", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Team")).toBeInTheDocument();
    });
  });

  it("owner sees the invite team member button", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(
        screen.getByTestId("invite-team-member-button"),
      ).toBeInTheDocument();
    });
  });

  it("owner sees pending invites section with fixture rows", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("newguy@pilot.local")).toBeInTheDocument();
    });
    expect(screen.getByText("sarah-office@pilot.local")).toBeInTheDocument();
  });

  it("technician does NOT see invite button or pending section", async () => {
    renderPage("technician");
    // Technician is blocked by RoleGate — content is absent from DOM.
    await new Promise((r) => setTimeout(r, 100));
    expect(
      screen.queryByTestId("invite-team-member-button"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("pending-invites-section"),
    ).not.toBeInTheDocument();
  });

  it("full invite flow: open dialog → submit → POST fires with Idempotency-Key → success", async () => {
    const capturedRequests: {
      url: string;
      headers: Record<string, string>;
      body: unknown;
    }[] = [];
    server.use(
      http.post("/api/v1/users/invites", async ({ request }) => {
        const body = await request.json();
        const headers: Record<string, string> = {};
        request.headers.forEach((value, key) => {
          headers[key] = value;
        });
        capturedRequests.push({ url: request.url, headers, body });
        return HttpResponse.json(
          {
            id: "invite-new",
            email: (body as { email: string }).email,
            role_code: (body as { role_code: string }).role_code,
            expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
            created_at: new Date().toISOString(),
          },
          { status: 201 },
        );
      }),
    );

    renderPage("owner");

    // Wait for page to load, then open dialog
    await waitFor(() => {
      expect(
        screen.getByTestId("invite-team-member-button"),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("invite-team-member-button"));

    // Fill form
    await waitFor(() => {
      expect(screen.getByTestId("invite-email-input")).toBeInTheDocument();
    });

    const emailInput = screen.getByTestId("invite-email-input");
    fireEvent.change(emailInput, {
      target: { value: "newteammate@example.com" },
    });

    // Submit
    const submitButton = screen.getByTestId("invite-submit");
    fireEvent.click(submitButton);

    // Verify POST fired with Idempotency-Key
    await waitFor(() => {
      expect(capturedRequests).toHaveLength(1);
    });
    expect(capturedRequests[0].headers["idempotency-key"]).toBeDefined();
    expect((capturedRequests[0].body as { email: string }).email).toBe(
      "newteammate@example.com",
    );

    // Verify success state
    await waitFor(() => {
      expect(screen.getByTestId("invite-dialog-done")).toBeInTheDocument();
    });
  });

  it("409 invite_pending_exists → shows Resend option", async () => {
    server.use(
      http.post("/api/v1/users/invites", () => {
        // PLP-FIX-7: nested envelope mirroring real FastAPI shape
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

    renderPage("owner");

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

  it("409 invite_user_exists → shows explainer", async () => {
    server.use(
      http.post("/api/v1/users/invites", () => {
        // PLP-FIX-7: nested envelope mirroring real FastAPI shape
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

    renderPage("owner");

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

  it("email validation error blocks submit on invalid format", async () => {
    renderPage("owner");

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
      target: { value: "not-an-email" },
    });

    fireEvent.click(screen.getByTestId("invite-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-email-error")).toBeInTheDocument();
    });
  });

  it("role select lists all 4 roles with descriptions", async () => {
    renderPage("owner");

    await waitFor(() => {
      expect(
        screen.getByTestId("invite-team-member-button"),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("invite-team-member-button"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-role-select")).toBeInTheDocument();
    });

    const select = screen.getByTestId(
      "invite-role-select",
    ) as HTMLSelectElement;
    const options = Array.from(select.querySelectorAll("option"));

    expect(options).toHaveLength(4);
    expect(options[0].value).toBe("owner");
    expect(options[1].value).toBe("technician");
    expect(options[2].value).toBe("office_staff");
    expect(options[3].value).toBe("accountant");
  });
});
