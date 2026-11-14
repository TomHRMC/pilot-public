/**
 * MFAEnrollmentWizard (mobile) — unit tests
 *
 * MFA-WIRE-1 Part C
 *
 * Location: packages/ui/src/mfa-enrollment-wizard/mobile/__tests__/MFAEnrollmentWizard.test.tsx
 *
 * Runs in the @pilot/ui vitest environment (jsdom + RN mock → HTML elements).
 * Uses vitest (vi), @testing-library/react, toBeInTheDocument() (web matchers).
 */
import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import {
  vi,
  beforeAll,
  afterAll,
  afterEach,
  describe,
  it,
  expect,
} from "vitest";
import { MFAEnrollmentWizard } from "../MFAEnrollmentWizard";

// ─── Mock aws-amplify/auth (dynamic import in the wizard) ────────────────────

vi.mock("aws-amplify/auth", () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: {
      accessToken: { toString: () => "mock-access-token" },
      idToken: { toString: () => "mock-id-token" },
    },
  }),
}));

// ─── MSW server ───────────────────────────────────────────────────────────────

let lastEnrollStartRequest: { headers: Headers } | null = null;
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- captures confirm body for debugging
let lastEnrollConfirmBody: { code?: string } | null = null;

const server = setupServer(
  // enroll-start — TOTP
  http.post(
    "*/api/v1/users/me/mfa/methods/totp/enroll-start",
    ({ request }) => {
      lastEnrollStartRequest = { headers: request.headers };
      return HttpResponse.json({
        method_type: "totp",
        qr_code_uri:
          "otpauth://totp/PilotForTrades:dev@pilot.local?secret=JBSWY3DPEHPK3PXP&issuer=PilotForTrades",
        secret: "JBSWY3DPEHPK3PXP",
      });
    },
  ),

  // enroll-start — SMS (default success)
  http.post("*/api/v1/users/me/mfa/methods/sms/enroll-start", ({ request }) => {
    lastEnrollStartRequest = { headers: request.headers };
    return HttpResponse.json({
      method_type: "sms",
      destination_masked: "•••0001",
    });
  }),

  // enroll-confirm — code matrix: 000000 → invalid, 999999 → expired, else 201
  http.post(
    "*/api/v1/users/me/mfa/methods/:methodType/enroll-confirm",
    async ({ request, params }) => {
      const body = (await request.json()) as { code?: string };
      lastEnrollConfirmBody = body;
      const methodType = params.methodType as string;

      if (body.code === "000000") {
        return HttpResponse.json(
          { code: "mfa_code_invalid", detail: "That code didn't match." },
          { status: 400 },
        );
      }
      if (body.code === "999999") {
        return HttpResponse.json(
          { code: "mfa_code_expired", detail: "That code has expired." },
          { status: 400 },
        );
      }
      return HttpResponse.json(
        {
          method_id: `${methodType}-method-0001`,
          enrolled_at: "2026-08-17T12:00:00Z",
        },
        { status: 201 },
      );
    },
  ),

  // recovery-codes/generate
  http.post("*/api/v1/users/me/mfa/recovery-codes/generate", () =>
    HttpResponse.json(
      {
        codes: ["ABCD-1234", "EFGH-5678", "IJKL-9012", "MNOP-3456"],
        set_id: "rc-set-0001",
      },
      { status: 201 },
    ),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  lastEnrollStartRequest = null;
  lastEnrollConfirmBody = null;
  vi.clearAllMocks();
});
afterAll(() => server.close());

// ─── Helpers ──────────────────────────────────────────────────────────────────

function renderWizard(props: Record<string, unknown> = {}) {
  const onComplete = vi.fn();
  const onCancel = vi.fn();
  render(
    <MFAEnrollmentWizard
      onComplete={onComplete}
      onCancel={onCancel}
      allowedPaths={["totp", "sms"]}
      {...props}
    />,
  );
  return { onComplete, onCancel };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("MFAEnrollmentWizard (mobile)", () => {
  it("1. chooser renders exactly two options (totp, sms) — no email", () => {
    renderWizard();

    expect(screen.getByTestId("mfa-path-totp")).toBeInTheDocument();
    expect(screen.getByTestId("mfa-path-sms")).toBeInTheDocument();
    expect(screen.queryByText(/email/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
  });

  it("2. selecting TOTP fires enroll-start with both auth headers", async () => {
    renderWizard();

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-path-totp"));
    });

    await waitFor(() => {
      expect(lastEnrollStartRequest).not.toBeNull();
    });

    expect(lastEnrollStartRequest!.headers.get("authorization")).toBe(
      "Bearer mock-id-token",
    );
    expect(lastEnrollStartRequest!.headers.get("x-cognito-access-token")).toBe(
      "mock-access-token",
    );
  });

  it("3. TOTP setup renders the grouped secret (4-char chunks)", async () => {
    renderWizard();

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-path-totp"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("totp-secret")).toBeInTheDocument();
    });

    expect(screen.getByTestId("totp-secret").textContent).toBe(
      "JBSW Y3DP EHPK 3PXP",
    );
  });

  it("4. verify: 6-digit entry enables Verify; 000000 → inline error; valid → complete", async () => {
    const { onComplete } = renderWizard({ showRecoveryCodes: false });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-path-totp"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("totp-secret")).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument();
    });

    const verifyBtn = screen.getByTestId("mfa-wizard-next");
    expect(verifyBtn).toBeDisabled();

    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "000000" },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-error")).toBeInTheDocument();
    });

    expect(screen.getByTestId("mfa-code-error").textContent).toContain(
      "That code didn't match",
    );

    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "123456" },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith("totp");
    });
  }, 15000);

  it("4b. verify: 999999 → mfa_code_expired inline error", async () => {
    renderWizard({ showRecoveryCodes: false });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-path-totp"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("totp-secret")).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "999999" },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-error")).toBeInTheDocument();
    });

    expect(screen.getByTestId("mfa-code-error").textContent).toContain(
      "expired",
    );
  }, 15000);

  it("5. SMS setup: masked destination shows; resend in cooldown", async () => {
    renderWizard();

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-path-sms"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("sms-destination")).toBeInTheDocument();
    });

    expect(screen.getByTestId("sms-destination").textContent).toBe("•••0001");

    // Resend should be in cooldown (30s) — verify initial state
    const resendBtn = screen.getByTestId("sms-resend");
    expect(resendBtn.textContent).toMatch(/Resend code in \d+s/);
  }, 15000);

  it("6. 503 sms_delivery_not_configured → warning + TOTP nudge; no haptic", async () => {
    server.use(
      http.post("*/api/v1/users/me/mfa/methods/sms/enroll-start", () =>
        HttpResponse.json(
          {
            code: "sms_delivery_not_configured",
            detail: "SMS delivery not configured.",
          },
          { status: 503 },
        ),
      ),
    );

    const hapticsModule = await import("expo-haptics");

    renderWizard();

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-path-sms"));
    });

    await waitFor(
      () => {
        expect(screen.getByTestId("wizard-error")).toBeInTheDocument();
      },
      { timeout: 10000 },
    );

    expect(screen.getByTestId("wizard-error").textContent).toContain(
      "temporarily unavailable",
    );

    expect(
      screen.getByTestId("sms-unavailable-totp-nudge"),
    ).toBeInTheDocument();

    // No haptic fired for warning (503)
    expect(hapticsModule.notificationAsync).not.toHaveBeenCalled();

    await act(async () => {
      fireEvent.click(screen.getByTestId("sms-unavailable-totp-nudge"));
    });

    await waitFor(
      () => {
        expect(screen.getByTestId("totp-secret")).toBeInTheDocument();
      },
      { timeout: 10000 },
    );
  }, 30000);

  it("7. recovery codes: showRecoveryCodes=true → Finish disabled until ack", async () => {
    renderWizard({ showRecoveryCodes: true });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-path-totp"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("totp-secret")).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "123456" },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(
      () => {
        expect(
          screen.getByTestId("recovery-codes-container"),
        ).toBeInTheDocument();
      },
      { timeout: 10000 },
    );

    const finishBtn = screen.getByTestId("mfa-wizard-finish");
    expect(finishBtn).toBeDisabled();

    await act(async () => {
      fireEvent.click(screen.getByTestId("recovery-codes-ack"));
    });

    expect(finishBtn).not.toBeDisabled();
  }, 30000);

  it("7b. recovery codes: showRecoveryCodes=false → no gate, onComplete fires", async () => {
    const { onComplete } = renderWizard({ showRecoveryCodes: false });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-path-totp"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("totp-secret")).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "123456" },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("mfa-wizard-next"));
    });

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith("totp");
    });

    expect(
      screen.queryByTestId("recovery-codes-container"),
    ).not.toBeInTheDocument();
  }, 15000);

  it("8. forceFlow hides Cancel and renders the warning banner", () => {
    renderWizard({ forceFlow: true });

    expect(screen.getByText(/organization requires MFA/i)).toBeInTheDocument();

    expect(screen.queryByText("Cancel")).not.toBeInTheDocument();
  });
});
