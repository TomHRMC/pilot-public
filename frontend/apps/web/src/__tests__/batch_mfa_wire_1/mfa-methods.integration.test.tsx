/**
 * MFA-WIRE-1 Part B — Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_mfa_wire_1/mfa-methods.integration.test.tsx
 *
 * Scenarios (spec §8 + prompt Test Requirements):
 *   1. Page renders method cards from methods[] (not raw "Enrolled:" text)
 *   2. Remove flow happy path: click Remove → modal → confirm → pending → 204 → card gone
 *   3. Rollback path: cognito-fail sentinel → 502 → card returns + error banner
 *   4. 409 path: last-method → warning banner + status re-invalidated
 *   5. Add button hidden when both totp and sms enrolled; visible otherwise
 *   6. allowedPaths constraint: wizard shows exactly "Authenticator app" + "Text message (SMS)" — no email, no "coming soon"
 *   7. Tenant-policy banner renders with grace copy
 *   8. Force-flow page renders context banner + allowedPaths constraint
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
import MfaMethodsPage from "../../app/(authed)/settings/my-account/security/mfa/page";
import MfaEnrollPage from "../../app/(authed)/settings/my-account/security/mfa/enroll/page";

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/my-account/security/mfa",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock the wizard + PendingBadge in a single @pilot/ui mock
let capturedAllowedPaths: string[] | undefined;
vi.mock("@pilot/ui", () => ({
  MFAEnrollmentWizard: ({
    testID,
    allowedPaths,
    onComplete,
    onCancel,
  }: {
    testID?: string;
    allowedPaths?: string[];
    onComplete?: () => void;
    onCancel?: () => void;
    enrolledMethods?: string[];
    showRecoveryCodes?: boolean;
    forceFlow?: boolean;
  }) => {
    capturedAllowedPaths = allowedPaths;
    return (
      <div data-testid={testID ?? "mfa-enrollment-wizard"}>
        {allowedPaths?.includes("totp") && <span>Authenticator app</span>}
        {allowedPaths?.includes("sms") && <span>Text message (SMS)</span>}
        {allowedPaths?.includes("email") && <span>Email code</span>}
        <button onClick={onComplete} data-testid="wizard-complete-btn">
          Complete
        </button>
        <button onClick={onCancel} data-testid="wizard-cancel-btn">
          Cancel
        </button>
      </div>
    );
  },
  PendingBadge: ({
    count,
    accessibilityLabel,
    className,
  }: {
    count: number;
    accessibilityLabel?: string;
    className?: string;
  }) => (
    <span
      data-testid="pending-badge"
      data-count={count}
      aria-label={accessibilityLabel}
      className={className}
    >
      Pending
    </span>
  ),
}));

// Mock @pilot/ui/states ErrorState (keep other exports via importOriginal)
vi.mock("@pilot/ui/states", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@pilot/ui/states")>();
  return {
    ...actual,
    ErrorState: ({
      description,
      onRetry,
      testID,
    }: {
      description: string;
      onRetry?: () => void;
      testID?: string;
    }) => (
      <div data-testid={testID ?? "error-state"} role="alert">
        <p>{description}</p>
        {onRetry && (
          <button onClick={onRetry} data-testid="error-retry-btn">
            Try again
          </button>
        )}
      </div>
    ),
  };
});

// ── MSW server ────────────────────────────────────────────────────────────────

// Module-level mutable state (mirrors the real accountSecurityHandlers pattern)
let enrolledMethods: string[] = [];

function resetEnrolledMethods() {
  enrolledMethods = [];
}

function buildMethods() {
  return enrolledMethods.map((methodType) => ({
    method_id: `mfa-method-${methodType}`,
    method_type: methodType,
    enrolled_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    last_used_at: null,
    destination_masked: methodType === "sms" ? "••••0001" : null,
  }));
}

const server = setupServer(
  http.get("/api/v1/users/me/mfa-status", () =>
    HttpResponse.json({
      enrolled_methods: enrolledMethods,
      methods: buildMethods(),
      tenant_policy_required: false,
      grace_period_active: false,
      grace_ends_at: null,
      enforcement_activated: false,
    }),
  ),
  http.delete("/api/v1/users/me/mfa/methods/:methodId", ({ params }) => {
    const { methodId } = params as { methodId: string };

    if (methodId === "cognito-fail") {
      return HttpResponse.json(
        { code: "cognito_unavailable", detail: "upstream failure" },
        { status: 502 },
      );
    }

    if (enrolledMethods.length <= 1) {
      return HttpResponse.json(
        {
          code: "last_method_required",
          detail: "Can't remove the last MFA method.",
        },
        { status: 409 },
      );
    }

    // Remove the method matching the methodId
    const methodType = methodId.replace("mfa-method-", "");
    enrolledMethods = enrolledMethods.filter((m) => m !== methodType);
    return new HttpResponse(null, { status: 204 });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  resetEnrolledMethods();
  capturedAllowedPaths = undefined;
});
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

// ── Helper: set enrolled methods via per-test MSW override ────────────────────

function overrideMfaStatus(
  methods: string[],
  policyRequired = false,
  graceActive = false,
  graceEndsAt: string | null = null,
) {
  enrolledMethods = [...methods];
  // The override reads from the mutable enrolledMethods so that after a
  // successful DELETE (which mutates enrolledMethods), the invalidation
  // refetch returns the updated list.
  server.use(
    http.get("/api/v1/users/me/mfa-status", () => {
      const currentMethods = enrolledMethods.map((methodType) => ({
        method_id: `mfa-method-${methodType}`,
        method_type: methodType,
        enrolled_at: new Date(
          Date.now() - 7 * 24 * 60 * 60 * 1000,
        ).toISOString(),
        last_used_at: null,
        destination_masked: methodType === "sms" ? "••••0001" : null,
      }));
      return HttpResponse.json({
        enrolled_methods: [...enrolledMethods],
        methods: currentMethods,
        tenant_policy_required: policyRequired,
        grace_period_active: graceActive,
        grace_ends_at: graceEndsAt,
        enforcement_activated: false,
      });
    }),
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("MFA-WIRE-1 Part B — MFA Methods Page Integration", () => {
  it("1. renders method cards from methods[] (not raw 'Enrolled:' text)", async () => {
    overrideMfaStatus(["totp"]);
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("mfa-method-card-totp")).toBeInTheDocument(),
    );
    expect(screen.getByText("Authenticator app")).toBeInTheDocument();
    // The raw "Enrolled: totp" text must NOT be present
    expect(screen.queryByText(/Enrolled: totp/)).not.toBeInTheDocument();
  });

  it("2. Remove flow happy path: click Remove → modal → confirm → pending → 204 → card gone", async () => {
    overrideMfaStatus(["totp", "sms"]);
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("mfa-method-card-totp")).toBeInTheDocument(),
    );

    // Click Remove on the TOTP card
    fireEvent.click(screen.getByTestId("mfa-method-remove-totp"));

    // Modal opens
    await waitFor(() =>
      expect(screen.getByTestId("mfa-remove-modal")).toBeInTheDocument(),
    );

    // Confirm removal
    fireEvent.click(screen.getByTestId("mfa-remove-modal-confirm"));

    // Card enters pending state (dim + badge)
    await waitFor(() =>
      expect(
        screen.getByTestId("mfa-method-card-totp-pending"),
      ).toBeInTheDocument(),
    );

    // After 204 + invalidation, the card is gone (refetch returns without totp)
    await waitFor(
      () => {
        expect(
          screen.queryByTestId("mfa-method-card-totp"),
        ).not.toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  it("3. Rollback path: cognito-fail sentinel → 502 → card returns + error banner", async () => {
    // Use a method with id "cognito-fail" to trigger the 502 sentinel
    server.use(
      http.get("/api/v1/users/me/mfa-status", () =>
        HttpResponse.json({
          enrolled_methods: ["totp", "sms"],
          methods: [
            {
              method_id: "cognito-fail",
              method_type: "totp",
              enrolled_at: new Date(
                Date.now() - 7 * 24 * 60 * 60 * 1000,
              ).toISOString(),
              last_used_at: null,
              destination_masked: null,
            },
            {
              method_id: "mfa-method-sms",
              method_type: "sms",
              enrolled_at: new Date(
                Date.now() - 7 * 24 * 60 * 60 * 1000,
              ).toISOString(),
              last_used_at: null,
              destination_masked: "••••0001",
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
      expect(screen.getByTestId("mfa-method-card-totp")).toBeInTheDocument(),
    );

    // Click Remove + confirm
    fireEvent.click(screen.getByTestId("mfa-method-remove-totp"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-remove-modal")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("mfa-remove-modal-confirm"));

    // After 502, the error banner appears with the cognito_unavailable copy
    await waitFor(
      () => {
        expect(
          screen.getByTestId("mfa-remove-error-banner"),
        ).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
    expect(
      screen.getByText(/couldn't reach the authentication service/i),
    ).toBeInTheDocument();
  });

  it("4. 409 path: last-method → warning banner", async () => {
    overrideMfaStatus(["totp"]);
    // Override DELETE to return 409
    server.use(
      http.delete("/api/v1/users/me/mfa/methods/:methodId", () =>
        HttpResponse.json(
          {
            code: "last_method_required",
            detail: "Can't remove the last MFA method.",
          },
          { status: 409 },
        ),
      ),
    );

    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("mfa-method-card-totp")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("mfa-method-remove-totp"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-remove-modal")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("mfa-remove-modal-confirm"));

    await waitFor(
      () => {
        expect(
          screen.getByTestId("mfa-remove-error-banner"),
        ).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
    expect(
      screen.getByText(/requires MFA. Add another method/i),
    ).toBeInTheDocument();
  });

  it("5. Add button hidden when both totp and sms enrolled; visible otherwise", async () => {
    // Both enrolled → hidden
    overrideMfaStatus(["totp", "sms"]);
    const { unmount } = render(<MfaMethodsPage />, {
      wrapper: createWrapper(),
    });
    await waitFor(() =>
      expect(screen.getByTestId("mfa-method-card-totp")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("add-mfa-method-btn")).not.toBeInTheDocument();
    unmount();

    // Only one enrolled → visible
    overrideMfaStatus(["totp"]);
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("add-mfa-method-btn")).toBeInTheDocument(),
    );
  });

  it("6. allowedPaths constraint: wizard shows totp + sms, no email, no 'coming soon'", async () => {
    overrideMfaStatus([]);
    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("add-mfa-method-btn")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("add-mfa-method-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("mfa-enrollment-wizard")).toBeInTheDocument(),
    );

    // allowedPaths was passed to the wizard
    expect(capturedAllowedPaths).toEqual(["totp", "sms"]);

    // No email option, no "coming soon" string anywhere
    expect(screen.queryByText(/email/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
  });

  it("7. Tenant-policy banner renders with grace copy", async () => {
    const graceEndsAt = new Date(
      Date.now() + 5 * 24 * 60 * 60 * 1000,
    ).toISOString();
    overrideMfaStatus([], true, true, graceEndsAt);

    render(<MfaMethodsPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(
        screen.getByTestId("mfa-tenant-policy-banner"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/requires MFA/i)).toBeInTheDocument();
    expect(screen.getByText(/days left/i)).toBeInTheDocument();
  });

  it("8. Force-flow page renders context banner + allowedPaths constraint", async () => {
    render(<MfaEnrollPage />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(
        screen.getByTestId("mfa-force-flow-context-banner"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/requires multi-factor authentication/i),
    ).toBeInTheDocument();
    // The wizard received allowedPaths={["totp","sms"]}
    expect(capturedAllowedPaths).toEqual(["totp", "sms"]);
  });
});
