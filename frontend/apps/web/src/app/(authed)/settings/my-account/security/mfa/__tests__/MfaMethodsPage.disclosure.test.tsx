/**
 * MFA Methods Page — Structure + Wizard Integration Tests (DLC-2)
 *
 * The SMS compliance disclosure (data-testid="sms-consent-disclosure") lives
 * inside MFAEnrollmentWizard (@pilot/ui) and is tested in:
 *   packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.test.tsx
 *
 * This file verifies the page-level structure of /settings/my-account/security/mfa.
 */
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import MfaMethodsPage from "../page";

// ── next/navigation mock ──────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/my-account/security/mfa",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// ── @pilot/ui mock ────────────────────────────────────────────────────────────

vi.mock("@pilot/ui", () => ({
  MFAEnrollmentWizard: ({
    testID,
  }: {
    testID?: string;
    onComplete?: () => void;
    onCancel?: () => void;
    enrolledMethods?: string[];
    showRecoveryCodes?: boolean;
    forceFlow?: boolean;
  }) => (
    <div data-testid={testID ?? "mfa-enrollment-wizard"}>
      MFAEnrollmentWizard
    </div>
  ),
}));

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/users/me/mfa-status", () =>
    HttpResponse.json({
      enrolled_methods: [],
      methods: [],
      tenant_policy_required: false,
      grace_period_active: false,
      grace_ends_at: null,
      enforcement_activated: false,
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Query wrapper ─────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("MfaMethodsPage — page structure (DLC-2)", () => {
  it("renders page title 'Two-factor authentication'", async () => {
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByText("Two-factor authentication")).toBeInTheDocument(),
    );
  });

  it("shows 'No authentication methods enrolled' when methods is empty", async () => {
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(
        screen.getByText("No authentication methods enrolled"),
      ).toBeInTheDocument(),
    );
  });

  it("renders 'Add a method' button", async () => {
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("add-mfa-method-btn")).toBeInTheDocument(),
    );
  });

  it("clicking 'Add a method' renders the MFAEnrollmentWizard", async () => {
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("add-mfa-method-btn")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("add-mfa-method-btn"));
    expect(screen.getByTestId("mfa-wizard-container")).toBeInTheDocument();
    expect(screen.getByTestId("mfa-enrollment-wizard")).toBeInTheDocument();
  });

  // MFA-WIRE-1: cards replace the raw "Enrolled: totp" text block.
  // Assert the card label + testid; the DLC-2 SMS disclosure still lives
  // inside the wizard's SmsSetupStep (not duplicated on the page).
  it("shows method card when MSW returns non-empty methods", async () => {
    server.use(
      http.get("/api/v1/users/me/mfa-status", () =>
        HttpResponse.json({
          enrolled_methods: ["totp"],
          methods: [
            {
              method_id: "mfa-method-totp",
              method_type: "totp",
              enrolled_at: new Date(
                Date.now() - 7 * 24 * 60 * 60 * 1000,
              ).toISOString(),
              last_used_at: null,
              destination_masked: null,
            },
          ],
          tenant_policy_required: false,
          grace_period_active: false,
          grace_ends_at: null,
          enforcement_activated: false,
        }),
      ),
    );
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByText("Authenticator app")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("mfa-method-card-totp")).toBeInTheDocument();
  });
});
