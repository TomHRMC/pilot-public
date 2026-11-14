/**
 * SIGNUP-UI-FIX-2 Task 4 — Resend text link on double-opt-in confirm screen
 *
 * Location: apps/web/src/__tests__/batch_signup_ui_fix_2/resend_optin.test.tsx
 *
 * Verifies:
 *  - Resend button fires POST /phone/send-optin with the correct body
 *    (user_endpoint_id retained from the consent response).
 *  - Button disabled with countdown copy after a successful send (60s).
 *  - 429 surfaces the cooldown copy ("We just sent a text. Wait a moment…").
 *  - Success shows a role="status" confirmation.
 *  - Resend button is hidden once `confirmed` is true.
 *  - Resend button is hidden when no onResend prop is provided.
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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { WIZARD_TENANT_ID_KEY } from "@/features/signup/types";

const { replace, push } = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import SignupPhonePage from "@/app/signup/phone/page";
import { DoubleOptinConfirmSubscreen } from "@/features/signup/components/DoubleOptinConfirmSubscreen";

// ── MSW server ──────────────────────────────────────────────────────────────
const TENANT = "tenant-resend-test-001";
const USER_ENDPOINT_ID = "ue-resend-test-001";

const sendOptinCalls: Array<{ body: unknown }> = [];

const server = setupServer(
  http.get(`/api/v1/signup/${TENANT}/state`, () =>
    HttpResponse.json({
      tenant_id: TENANT,
      signup_state: "step2_legal",
      collected_data: { owner_first_name: "Mike" },
    }),
  ),
  http.post(`/api/v1/signup/${TENANT}/phone/consent`, () =>
    HttpResponse.json(
      { user_endpoint_id: USER_ENDPOINT_ID, verification_status: "pending" },
      { status: 201 },
    ),
  ),
  http.post(
    `/api/v1/signup/${TENANT}/phone/send-optin`,
    async ({ request }) => {
      const body = await request.json();
      sendOptinCalls.push({ body });
      return HttpResponse.json({ status: "sent" });
    },
  ),
  http.put(`/api/v1/signup/${TENANT}/step3`, () =>
    HttpResponse.json({
      tenant_id: TENANT,
      signup_state: "step3_phone",
      next_step: "plan",
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  sendOptinCalls.length = 0;
});
afterAll(() => server.close());

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

const notAuthValue: AuthContextValue = {
  user: null,
  isAuthenticated: false,
  role: null,
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("mock-token"),
};

function renderWithProvider(ui: React.ReactElement) {
  return render(
    <AuthContext.Provider value={notAuthValue}>
      <QueryClientProvider client={makeQueryClient()}>{ui}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

beforeEach(() => {
  replace.mockClear();
  push.mockClear();
  sendOptinCalls.length = 0;
  sessionStorage.clear();
  sessionStorage.setItem(WIZARD_TENANT_ID_KEY, TENANT);
});

// ── Helper: submit the consent form to reach the confirm subscreen ──────────
async function submitConsentForm() {
  renderWithProvider(<SignupPhonePage />);
  await waitFor(() => {
    expect(screen.getByTestId("signup-stayinformed-form")).toBeInTheDocument();
  });
  fireEvent.change(screen.getByTestId("field-phone-number"), {
    target: { value: "+15551234567" },
  });
  fireEvent.click(screen.getByTestId("signup-sms-consent-checkbox"));
  fireEvent.click(screen.getByTestId("signup-stayinformed-continue"));
  await waitFor(() => {
    expect(screen.getByTestId("double-optin-confirm")).toBeInTheDocument();
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// Integration tests (page-level — resend fires through phone/page.tsx)
// ═══════════════════════════════════════════════════════════════════════════

describe("SIGNUP-UI-FIX-2 Task 4 — Resend (page integration)", () => {
  it("resend fires POST /phone/send-optin with the retained user_endpoint_id", async () => {
    await submitConsentForm();

    // The initial send-optin from handleSubmit already fired.
    const initialCount = sendOptinCalls.length;
    expect(initialCount).toBeGreaterThanOrEqual(1);

    // Click Resend.
    fireEvent.click(screen.getByTestId("double-optin-resend"));

    await waitFor(() => {
      expect(sendOptinCalls.length).toBe(initialCount + 1);
    });

    // The resend body must carry the user_endpoint_id.
    expect(sendOptinCalls[sendOptinCalls.length - 1].body).toMatchObject({
      user_endpoint_id: USER_ENDPOINT_ID,
    });
  });

  it("success shows a role=status confirmation", async () => {
    await submitConsentForm();

    fireEvent.click(screen.getByTestId("double-optin-resend"));

    await waitFor(() => {
      expect(
        screen.getByTestId("double-optin-resend-success"),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId("double-optin-resend-success")).toHaveTextContent(
      "Text sent. Reply YES to confirm.",
    );
  });

  it("button disabled with countdown copy after a successful send", async () => {
    await submitConsentForm();

    fireEvent.click(screen.getByTestId("double-optin-resend"));

    await waitFor(() => {
      expect(screen.getByTestId("double-optin-resend")).toBeDisabled();
    });
    expect(screen.getByTestId("double-optin-resend")).toHaveTextContent(
      /Resend text \(available in \d+s\)/,
    );
  });

  it("429 surfaces the cooldown copy and starts the countdown", async () => {
    // First submit the consent form with the default (200) send-optin
    // handler so the confirm subscreen renders.
    await submitConsentForm();

    // NOW override send-optin to return 429 for the resend attempt.
    server.use(
      http.post(`/api/v1/signup/${TENANT}/phone/send-optin`, () =>
        HttpResponse.json(
          { detail: "Too many requests. Wait before resending." },
          { status: 429 },
        ),
      ),
    );

    fireEvent.click(screen.getByTestId("double-optin-resend"));

    await waitFor(() => {
      expect(
        screen.getByTestId("double-optin-resend-error"),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId("double-optin-resend-error")).toHaveTextContent(
      /We just sent a text. Wait a moment/i,
    );

    // Button should be disabled with countdown after 429.
    await waitFor(() => {
      expect(screen.getByTestId("double-optin-resend")).toBeDisabled();
    });
  });

  it("resend button is hidden once confirmed is true", async () => {
    await submitConsentForm();

    // Before confirm: resend button is visible.
    expect(screen.getByTestId("double-optin-resend")).toBeInTheDocument();

    // Simulate the YES reply by overriding /state to return opted_in.
    server.use(
      http.get(`/api/v1/signup/${TENANT}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT,
          signup_state: "step2_legal",
          collected_data: {
            owner_first_name: "Mike",
            sms_consent_status: "opted_in",
          },
        }),
      ),
    );

    // Wait for the polling to detect opted_in → confirmed banner.
    await waitFor(
      () => {
        expect(
          screen.getByTestId("double-optin-confirmed"),
        ).toBeInTheDocument();
      },
      { timeout: 10000 },
    );

    // After confirm: resend button is gone.
    expect(screen.queryByTestId("double-optin-resend")).toBeNull();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Unit tests (subscreen component — isolated)
// ═══════════════════════════════════════════════════════════════════════════

describe("SIGNUP-UI-FIX-2 Task 4 — DoubleOptinConfirmSubscreen (unit)", () => {
  it("resend button is hidden when onResend is not provided", () => {
    render(
      <DoubleOptinConfirmSubscreen
        maskedPhone="+1 (•••) •••-4567"
        confirmed={false}
        onUseDifferentNumber={() => {}}
        onSkipForNow={() => {}}
      />,
    );
    expect(screen.queryByTestId("double-optin-resend")).toBeNull();
  });

  it("resend button is hidden when confirmed is true (even with onResend)", () => {
    render(
      <DoubleOptinConfirmSubscreen
        maskedPhone="+1 (•••) •••-4567"
        confirmed={true}
        onUseDifferentNumber={() => {}}
        onSkipForNow={() => {}}
        onResend={async () => ({ ok: true })}
      />,
    );
    expect(screen.queryByTestId("double-optin-resend")).toBeNull();
  });

  it("resend button is visible when onResend is provided and not confirmed", () => {
    render(
      <DoubleOptinConfirmSubscreen
        maskedPhone="+1 (•••) •••-4567"
        confirmed={false}
        onUseDifferentNumber={() => {}}
        onSkipForNow={() => {}}
        onResend={async () => ({ ok: true })}
      />,
    );
    expect(screen.getByTestId("double-optin-resend")).toBeInTheDocument();
    expect(screen.getByTestId("double-optin-resend")).toHaveTextContent(
      "Resend text",
    );
  });

  it("calls onResend when clicked and shows success", async () => {
    const onResend = vi.fn().mockResolvedValue({ ok: true });
    render(
      <DoubleOptinConfirmSubscreen
        maskedPhone="+1 (•••) •••-4567"
        confirmed={false}
        onUseDifferentNumber={() => {}}
        onSkipForNow={() => {}}
        onResend={onResend}
      />,
    );

    fireEvent.click(screen.getByTestId("double-optin-resend"));

    await waitFor(() => {
      expect(onResend).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("double-optin-resend-success"),
      ).toBeInTheDocument();
    });
  });

  it("429 error from onResend surfaces the cooldown copy", async () => {
    const onResend = vi.fn().mockResolvedValue({
      ok: false,
      error: "We just sent a text. Wait a moment before trying again.",
    });
    render(
      <DoubleOptinConfirmSubscreen
        maskedPhone="+1 (•••) •••-4567"
        confirmed={false}
        onUseDifferentNumber={() => {}}
        onSkipForNow={() => {}}
        onResend={onResend}
      />,
    );

    fireEvent.click(screen.getByTestId("double-optin-resend"));

    await waitFor(() => {
      expect(
        screen.getByTestId("double-optin-resend-error"),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId("double-optin-resend-error")).toHaveTextContent(
      /We just sent a text. Wait a moment/i,
    );
  });
});
