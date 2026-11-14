/**
 * TEAM-INVITE-1 Integration Tests — Invite Landing Page
 *
 * Location: apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx
 *
 * Verifies:
 *   1. Valid token renders the join panel + CTA href
 *   2. Unknown token renders the neutral invalid state
 *   3. Non-404 error renders retry state
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InviteLandingPage } from "@/features/users/components/InviteLandingPage";

// ─── MSW server ────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/invites/:token", ({ params }) => {
    if (params.token !== "dev-invite-token-0001") {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/invite_invalid",
          title: "Invite invalid",
          status: 404,
          detail: "This invite link is no longer valid.",
        },
        { status: 404 },
      );
    }

    return HttpResponse.json({
      tenant_name: "Pilot Dev Tenant",
      email: "newguy@pilot.local",
      role_code: "technician",
      expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
    });
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── Tests ─────────────────────────────────────────────────────────────────

describe("TEAM-INVITE-1 — Invite Landing Page", () => {
  it("valid token renders the join panel with tenant name, email, role, and accept form", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <InviteLandingPage token="dev-invite-token-0001" />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("invite-landing-page")).toBeInTheDocument();
    });

    expect(screen.getByText("Pilot Dev Tenant")).toBeInTheDocument();
    expect(
      screen.getAllByText("newguy@pilot.local").length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Field Technician")).toBeInTheDocument();

    // TEAM-INVITE-2: the old /signup CTA link is gone; the accept form is present.
    expect(screen.getByTestId("invite-accept-form")).toBeInTheDocument();
    expect(screen.getByTestId("invite-accept-submit")).toBeInTheDocument();
    expect(screen.queryByTestId("invite-signup-cta")).toBeNull();
  });

  it("unknown token renders the neutral invalid state", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <InviteLandingPage token="unknown-token-xyz" />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("invite-invalid-page")).toBeInTheDocument();
    });

    expect(
      screen.getByText("This invite link is no longer valid."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Ask the business owner to send you a fresh invite."),
    ).toBeInTheDocument();
  });

  it("non-404 error renders retry state", async () => {
    server.use(
      http.get("/api/v1/invites/:token", () => {
        return HttpResponse.json(
          { detail: "Internal server error" },
          { status: 500 },
        );
      }),
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <InviteLandingPage token="dev-invite-token-0001" />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("invite-error-page")).toBeInTheDocument();
    });

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Try again")).toBeInTheDocument();
  });
});
