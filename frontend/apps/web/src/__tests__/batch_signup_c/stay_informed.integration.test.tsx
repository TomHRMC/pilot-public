/**
 * SIGNUP-C — "Stay Informed" Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_signup_c/stay_informed.integration.test.tsx
 *
 * Integration coverage per the React Engineer prompt:
 *  - Page renders (not 404); progress bar present.
 *  - Phone + consent checked → Continue fires POST /phone/consent, then
 *    POST /phone/send-optin, then PUT /step3 (assert method+URL+body order);
 *    routes to /signup/plan.
 *  - Consent left unchecked → Continue fires POST /phone/consent
 *    (sms_consent:false) → NO send-optin → PUT /step3 → /signup/plan.
 *  - Reply-YES sub-state renders after send-optin; "Use a different number"
 *    returns to the form.
 *
 * Asserts by specific content/IDs from MSW fixtures — never total counts.
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

// ── Hoisted navigation mock ─────────────────────────────────────────────────
const { replace, push } = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import SignupPhonePage from "@/app/signup/phone/page";

// ── MSW server ──────────────────────────────────────────────────────────────
const TENANT = "tenant-test-00000000-0000-0000-0000-000000000001";
const USER_ENDPOINT_ID = "ue-test-00000000-0000-0000-0000-000000000001";

// Track call order for the consent-checked flow.
const callLog: Array<{ method: string; url: string; body?: unknown }> = [];

const server = setupServer(
  // /state — returns step2_legal (user belongs on the phone page).
  http.get(`/api/v1/signup/${TENANT}/state`, () => {
    callLog.push({ method: "GET", url: `/api/v1/signup/${TENANT}/state` });
    return HttpResponse.json({
      tenant_id: TENANT,
      signup_state: "step2_legal",
      collected_data: { owner_first_name: "Mike" },
    });
  }),

  // POST /phone/consent
  http.post(`/api/v1/signup/${TENANT}/phone/consent`, async ({ request }) => {
    const body = await request.json();
    callLog.push({
      method: "POST",
      url: `/api/v1/signup/${TENANT}/phone/consent`,
      body,
    });
    return HttpResponse.json(
      { user_endpoint_id: USER_ENDPOINT_ID, verification_status: "pending" },
      { status: 201 },
    );
  }),

  // POST /phone/send-optin
  http.post(
    `/api/v1/signup/${TENANT}/phone/send-optin`,
    async ({ request }) => {
      const body = await request.json();
      callLog.push({
        method: "POST",
        url: `/api/v1/signup/${TENANT}/phone/send-optin`,
        body,
      });
      return HttpResponse.json({ status: "sent" });
    },
  ),

  // PUT /step3
  http.put(`/api/v1/signup/${TENANT}/step3`, async ({ request }) => {
    const body = await request.json();
    callLog.push({
      method: "PUT",
      url: `/api/v1/signup/${TENANT}/step3`,
      body,
    });
    return HttpResponse.json({
      tenant_id: TENANT,
      signup_state: "step3_phone",
      next_step: "plan",
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  callLog.length = 0;
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

// SIGNUP-UI-FIX-1: phone page now uses useAuth() — provide a not-authenticated context
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
  callLog.length = 0;
  sessionStorage.clear();
  sessionStorage.setItem(WIZARD_TENANT_ID_KEY, TENANT);
});

describe("SIGNUP-C — Stay Informed integration", () => {
  it("1. page renders (not 404); progress bar present", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });
    // Progress bar renders (wizard-step-dot-phone is the current step).
    expect(screen.getByTestId("wizard-step-dot-phone")).toBeInTheDocument();
    expect(screen.getByText("Stay informed")).toBeInTheDocument();
  });

  it("2. consent checked → Continue fires consent → send-optin → step3 (ordered); routes to /signup/plan", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });

    // Enter a valid phone.
    fireEvent.change(screen.getByTestId("field-phone-number"), {
      target: { value: "+15551234567" },
    });

    // Check the consent checkbox.
    fireEvent.click(screen.getByTestId("signup-sms-consent-checkbox"));

    // Submit.
    fireEvent.click(screen.getByTestId("signup-stayinformed-continue"));

    // Assert the ordered API calls: consent → send-optin → step3.
    await waitFor(() => {
      const consentCall = callLog.find(
        (c) => c.url === `/api/v1/signup/${TENANT}/phone/consent`,
      );
      const optinCall = callLog.find(
        (c) => c.url === `/api/v1/signup/${TENANT}/phone/send-optin`,
      );
      const step3Call = callLog.find(
        (c) => c.url === `/api/v1/signup/${TENANT}/step3`,
      );
      expect(consentCall).toBeDefined();
      expect(optinCall).toBeDefined();
      expect(step3Call).toBeDefined();

      // Order: consent index < optin index < step3 index.
      const consentIdx = callLog.indexOf(consentCall!);
      const optinIdx = callLog.indexOf(optinCall!);
      const step3Idx = callLog.indexOf(step3Call!);
      expect(consentIdx).toBeLessThan(optinIdx);
      expect(optinIdx).toBeLessThan(step3Idx);
    });

    // consent body has sms_consent: true + disclosure_hash.
    const consentCall = callLog.find(
      (c) => c.url === `/api/v1/signup/${TENANT}/phone/consent`,
    );
    expect(consentCall?.body).toMatchObject({
      phone_number: "+15551234567",
      sms_consent: true,
      disclosure_hash: expect.any(String),
    });

    // send-optin body has user_endpoint_id.
    const optinCall = callLog.find(
      (c) => c.url === `/api/v1/signup/${TENANT}/phone/send-optin`,
    );
    expect(optinCall?.body).toMatchObject({
      user_endpoint_id: USER_ENDPOINT_ID,
    });

    // step3 body has phone_number + sms_consent: true.
    const step3Call = callLog.find(
      (c) => c.url === `/api/v1/signup/${TENANT}/step3`,
    );
    expect(step3Call?.body).toMatchObject({
      phone_number: "+15551234567",
      sms_consent: true,
    });

    // After the ordered calls, the confirm sub-state renders (reply-YES panel).
    await waitFor(() => {
      expect(screen.getByTestId("double-optin-confirm")).toBeInTheDocument();
    });
  });

  it("3. consent unchecked → Continue fires step3 (sms_consent:false); NO send-optin; routes to /signup/plan", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });

    // Enter a valid phone. Do NOT check the consent box (unchecked by default).
    fireEvent.change(screen.getByTestId("field-phone-number"), {
      target: { value: "+15551234567" },
    });

    // Submit.
    fireEvent.click(screen.getByTestId("signup-stayinformed-continue"));

    // Assert NO consent call, NO send-optin call, step3 called with sms_consent:false.
    await waitFor(() => {
      const step3Call = callLog.find(
        (c) => c.url === `/api/v1/signup/${TENANT}/step3`,
      );
      expect(step3Call).toBeDefined();
      expect(step3Call?.body).toMatchObject({
        phone_number: "+15551234567",
        sms_consent: false,
      });
    });

    // No consent or send-optin calls.
    const consentCall = callLog.find(
      (c) => c.url === `/api/v1/signup/${TENANT}/phone/consent`,
    );
    const optinCall = callLog.find(
      (c) => c.url === `/api/v1/signup/${TENANT}/phone/send-optin`,
    );
    expect(consentCall).toBeUndefined();
    expect(optinCall).toBeUndefined();

    // Routes directly to /signup/plan (no confirm sub-state).
    await waitFor(() => {
      expect(push).toHaveBeenCalledWith("/signup/plan");
    });
  });

  it("4. reply-YES sub-state renders after send-optin; 'Use a different number' returns to the form", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });

    // Enter phone + check consent + submit.
    fireEvent.change(screen.getByTestId("field-phone-number"), {
      target: { value: "+15551234567" },
    });
    fireEvent.click(screen.getByTestId("signup-sms-consent-checkbox"));
    fireEvent.click(screen.getByTestId("signup-stayinformed-continue"));

    // Confirm sub-state renders.
    await waitFor(() => {
      expect(screen.getByTestId("double-optin-confirm")).toBeInTheDocument();
    });

    // The masked phone appears in the body text.
    expect(screen.getByText(/4567/)).toBeInTheDocument();

    // "Use a different number" returns to the form.
    fireEvent.click(screen.getByTestId("double-optin-use-different-number"));

    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });
    // The confirm sub-state is gone.
    expect(screen.queryByTestId("double-optin-confirm")).toBeNull();
  });
});
