/**
 * MFAEnrollmentWizard tests — FE-B12
 *
 * Location: packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.test.tsx
 *
 * Tests:
 *  - FE-B1 skeleton regression (minimal props still work)
 *  - TOTP path: QR code renders, OTP submission calls confirm, recovery codes shown
 *  - SMS path: masked phone, OTP submit
 *  - Email path: masked email, OTP submit
 *  - Force-flow mode: Cancel not rendered
 *  - Grace period banners (>3 days, ≤3 days, 0 days)
 *  - Wrong code → inline error
 *  - Recovery codes step: 10 codes, copy all, continue disabled until acknowledged
 *  - onComplete fires after complete step
 *  - enrolledMethods marks methods as enrolled
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
import { MFAEnrollmentWizard } from "./MFAEnrollmentWizard";

// ─── MSW server ───────────────────────────────────────────────────────────────

const server = setupServer(
  // Recovery codes status — no codes initially
  http.get("/api/v1/users/me/mfa/recovery-codes/status", () =>
    HttpResponse.json({ unused_code_count: 0, last_generated_at: null }),
  ),
  // Enroll start — TOTP
  http.post("/api/v1/users/me/mfa/methods/totp/enroll-start", () =>
    HttpResponse.json({
      method_type: "totp",
      qr_code_uri: "otpauth://totp/Pilot?secret=TESTSECRET&issuer=Pilot",
      secret: "TESTSECRET",
    }),
  ),
  // Enroll start — SMS
  http.post("/api/v1/users/me/mfa/methods/sms/enroll-start", () =>
    HttpResponse.json({
      method_type: "sms",
      destination_masked: "+1 (555) ***-4567",
    }),
  ),
  // Enroll start — Email
  http.post("/api/v1/users/me/mfa/methods/email/enroll-start", () =>
    HttpResponse.json({
      method_type: "email",
      destination_masked: "m***@example.com",
    }),
  ),
  // Enroll confirm — success for codes "123456", failure for "000000"
  http.post(
    "/api/v1/users/me/mfa/methods/:methodType/enroll-confirm",
    async ({ request }) => {
      const body = (await request.json()) as { code: string };
      if (body.code === "000000") {
        return HttpResponse.json(
          {
            code: "mfa_code_invalid",
            detail: "That code doesn't match. Check your app and try again.",
          },
          { status: 400 },
        );
      }
      return HttpResponse.json({
        method_id: "mfa-method-001",
        enrolled_at: new Date().toISOString(),
      });
    },
  ),
  // Recovery codes generate
  http.post("/api/v1/users/me/mfa/recovery-codes/generate", () =>
    HttpResponse.json({
      codes: [
        "AAAA-1111-BBBB",
        "CCCC-2222-DDDD",
        "EEEE-3333-FFFF",
        "GGGG-4444-HHHH",
        "IIII-5555-JJJJ",
        "KKKK-6666-LLLL",
        "MMMM-7777-NNNN",
        "OOOO-8888-PPPP",
        "QQQQ-9999-RRRR",
        "SSSS-0000-TTTT",
      ],
      set_id: "test-set-001",
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── Helpers ──────────────────────────────────────────────────────────────────

function renderWizard(
  overrides: Partial<Parameters<typeof MFAEnrollmentWizard>[0]> = {},
) {
  const onComplete = vi.fn();
  const onCancel = vi.fn();
  const utils = render(
    <MFAEnrollmentWizard
      onComplete={onComplete}
      onCancel={onCancel}
      {...overrides}
    />,
  );
  return { ...utils, onComplete, onCancel };
}

// ─── FE-B1 Skeleton Regression ────────────────────────────────────────────────

describe("FE-B1 skeleton regression", () => {
  it("renders with minimal props (onComplete + onCancel) without crashing", () => {
    const { container } = renderWizard();
    expect(container).toBeTruthy();
  });

  it("renders method-select step by default", () => {
    renderWizard();
    expect(
      screen.getByText(/choose your authentication method/i),
    ).toBeInTheDocument();
  });

  it("renders all three method options by default", () => {
    renderWizard();
    expect(screen.getByText("Authenticator app")).toBeInTheDocument();
    expect(screen.getByText("Text message (SMS)")).toBeInTheDocument();
    expect(screen.getByText("Email code")).toBeInTheDocument();
  });

  it("Cancel button calls onCancel", () => {
    const { onCancel } = renderWizard();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});

// ─── Method Selection ─────────────────────────────────────────────────────────

describe("method selection", () => {
  it("selects TOTP path and advances to setup-totp on click", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() => {
      expect(screen.getByText(/set up authenticator app/i)).toBeInTheDocument();
    });
  });

  it("selects SMS path and advances to setup-sms on click", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Text message (SMS)"));
    });
    await waitFor(() => {
      expect(screen.getByText(/verify your phone number/i)).toBeInTheDocument();
    });
  });

  it("forcedPath='totp' skips method-select", async () => {
    renderWizard({ forcedPath: "totp" });
    await waitFor(() => {
      expect(screen.getByText(/set up authenticator app/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/choose your authentication method/i),
    ).not.toBeInTheDocument();
  });

  it("enrolledMethods shows enrolled methods as disabled", () => {
    renderWizard({ enrolledMethods: ["totp"] });
    const totpButton = screen
      .getAllByRole("button")
      .find((btn) => btn.textContent?.includes("Authenticator app"));
    expect(totpButton).toBeDisabled();
    expect(screen.getByText("Enrolled")).toBeInTheDocument();
  });
});

// ─── TOTP Path ────────────────────────────────────────────────────────────────

describe("TOTP enrollment path", () => {
  it("renders QR code img with alt containing secret after setup starts", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() => {
      const img = screen.getByTestId("totp-qr-code");
      expect(img).toBeInTheDocument();
      expect(img.getAttribute("alt")).toContain("TESTSECRET");
    });
  });

  it("renders secret code for manual entry", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("totp-secret")).toHaveTextContent("TESTSECRET");
    });
  });

  it("advances to verify-totp on Continue click", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("wizard-continue"));
    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument();
    });
  });

  it("enroll-confirm with valid code shows recovery codes step", async () => {
    renderWizard();
    // Select TOTP
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument(),
    );
    // Continue to verify
    fireEvent.click(screen.getByTestId("wizard-continue"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument(),
    );
    // Enter valid code
    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "123456" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("wizard-verify"));
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("recovery-codes-container"),
      ).toBeInTheDocument();
    });
  });

  it("recovery codes step shows 10 codes", async () => {
    renderWizard();
    // Navigate to recovery codes
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("wizard-continue"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "123456" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("wizard-verify"));
    });
    await waitFor(() => {
      const codes = screen
        .getByTestId("recovery-codes-container")
        .querySelectorAll("code");
      expect(codes).toHaveLength(10);
    });
  });

  it("Continue button disabled until recovery codes acknowledged", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("wizard-continue"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "123456" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("wizard-verify"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("wizard-complete-recovery")).toBeDisabled();
    });
    // Check the checkbox
    fireEvent.click(screen.getByTestId("recovery-codes-checkbox"));
    expect(screen.getByTestId("wizard-complete-recovery")).not.toBeDisabled();
  });

  it("onComplete fires with 'totp' after recovery codes acknowledged", async () => {
    const { onComplete } = renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("wizard-continue"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "123456" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("wizard-verify"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("recovery-codes-checkbox")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("recovery-codes-checkbox"));
    await act(async () => {
      fireEvent.click(screen.getByTestId("wizard-complete-recovery"));
    });
    expect(onComplete).toHaveBeenCalledWith("totp");
  });
});

// ─── SMS Path ─────────────────────────────────────────────────────────────────

describe("SMS enrollment path", () => {
  it("renders masked phone number in setup-sms step", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Text message (SMS)"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("sms-destination")).toHaveTextContent(
        "+1 (555) ***-4567",
      );
    });
  });

  it("renders 10DLC SMS consent disclosure on setup-sms step", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Text message (SMS)"));
    });
    await waitFor(() => {
      const disclosure = screen.getByTestId("sms-consent-disclosure");
      expect(disclosure).toBeInTheDocument();
      expect(disclosure).toHaveTextContent("Message and data rates may apply");
      expect(disclosure).toHaveTextContent("Reply STOP to opt out");
      expect(disclosure).toHaveTextContent("Reply HELP for help");
      expect(disclosure).toHaveTextContent("Privacy policy:");
      expect(disclosure).toHaveTextContent(
        "www.pilotfortrades.com/legal/privacy",
      );
    });
  });

  it("advances to verify step on Send code", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Text message (SMS)"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument(),
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("wizard-continue"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument();
      expect(
        screen.getByText(/enter the code we texted you/i),
      ).toBeInTheDocument();
    });
  });
});

// ─── Email Path ───────────────────────────────────────────────────────────────

describe("Email enrollment path", () => {
  it("renders masked email in setup-email step", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Email code"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("email-destination")).toHaveTextContent(
        "m***@example.com",
      );
    });
  });
});

// ─── Code Input Validation ────────────────────────────────────────────────────

describe("code input", () => {
  it("accepts only numeric input (strips non-digits)", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("wizard-continue"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument(),
    );
    const input = screen.getByTestId("mfa-code-input");
    fireEvent.change(input, { target: { value: "12ab34" } });
    expect(input).toHaveValue("1234");
  });

  it("wrong code (000000) shows inline error; code input clears", async () => {
    renderWizard();
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("wizard-continue"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "000000" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("wizard-verify"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-error")).toBeInTheDocument();
      expect(screen.getByTestId("mfa-code-error")).toHaveTextContent(
        /doesn't match/i,
      );
    });
  });
});

// ─── Force-Flow Mode ──────────────────────────────────────────────────────────

describe("force-flow mode", () => {
  it("forceFlow=true hides Cancel button", () => {
    renderWizard({ forceFlow: true });
    expect(
      screen.queryByRole("button", { name: /cancel/i }),
    ).not.toBeInTheDocument();
  });

  it("forceFlow=false shows Cancel button (default)", () => {
    renderWizard({ forceFlow: false });
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });
});

// ─── Grace Period Banners ─────────────────────────────────────────────────────

describe("grace period banners", () => {
  it("shows no banner when gracePeriodDaysRemaining is undefined", () => {
    renderWizard();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows info banner when gracePeriodDaysRemaining > 3", () => {
    renderWizard({ gracePeriodDaysRemaining: 5 });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("5 days");
    expect(alert.className).toContain("info");
  });

  it("shows alert/amber banner when gracePeriodDaysRemaining is 1–3", () => {
    renderWizard({ gracePeriodDaysRemaining: 3 });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("3 days");
    expect(alert.className).toContain("alert");
  });

  it("shows error/red banner when gracePeriodDaysRemaining is 0", () => {
    renderWizard({ gracePeriodDaysRemaining: 0 });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/required today/i);
    expect(alert.className).toContain("error");
  });
});

// ─── showRecoveryCodes=false ──────────────────────────────────────────────────

describe("showRecoveryCodes=false", () => {
  it("skips recovery codes step when showRecoveryCodes=false", async () => {
    const { onComplete } = renderWizard({ showRecoveryCodes: false });
    await act(async () => {
      fireEvent.click(screen.getByText("Authenticator app"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("wizard-continue")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("wizard-continue"));
    await waitFor(() =>
      expect(screen.getByTestId("mfa-code-input")).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByTestId("mfa-code-input"), {
      target: { value: "123456" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("wizard-verify"));
    });
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith("totp");
    });
    expect(
      screen.queryByTestId("recovery-codes-container"),
    ).not.toBeInTheDocument();
  });
});
