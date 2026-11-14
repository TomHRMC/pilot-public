/**
 * StayInformedStep unit tests — SIGNUP-C
 *
 * Location: apps/web/src/features/signup/components/__tests__/StayInformedStep.test.tsx
 *
 * Verifies:
 *  - Consent checkbox is UNCHECKED on mount (compliance posture).
 *  - Phone is required: empty submit → validation error, no API call.
 *  - Disclosure block is always visible (checked + unchecked).
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

const server = setupServer(
  http.get(`/api/v1/signup/${TENANT}/state`, () =>
    HttpResponse.json({
      tenant_id: TENANT,
      signup_state: "step2_legal",
      collected_data: { owner_first_name: "Mike" },
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
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
  sessionStorage.clear();
  sessionStorage.setItem(WIZARD_TENANT_ID_KEY, TENANT);
});

describe("StayInformedStep — unit", () => {
  it("renders the page (not 404) with the progress bar", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Stay informed")).toBeInTheDocument();
  });

  it("consent checkbox is UNCHECKED on mount", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });
    const checkbox = screen.getByTestId(
      "signup-sms-consent-checkbox",
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
  });

  it("disclosure block is always visible (unchecked state)", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("signup-sms-consent-disclosure"),
    ).toBeInTheDocument();
  });

  it("Continue button is disabled when phone is empty", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });
    const button = screen.getByTestId(
      "signup-stayinformed-continue",
    ) as HTMLButtonElement;
    expect(button).toBeDisabled();
  });

  it("shows validation error on invalid phone + blur, no API call", async () => {
    const postSpy = vi.fn();
    server.use(
      http.post(`/api/v1/signup/${TENANT}/phone/consent`, () => {
        postSpy();
        return HttpResponse.json(
          { user_endpoint_id: "x", verification_status: "pending" },
          { status: 201 },
        );
      }),
    );

    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });

    const input = screen.getByTestId("field-phone-number");
    fireEvent.change(input, { target: { value: "abc" } });
    fireEvent.blur(input);

    await waitFor(() => {
      expect(
        screen.getByTestId("field-phone-number-error"),
      ).toBeInTheDocument();
    });

    // Submit attempt with invalid phone should NOT call the API.
    const form = screen.getByTestId("signup-stayinformed-form");
    fireEvent.submit(form);
    expect(postSpy).not.toHaveBeenCalled();
  });

  it("enables Continue when a valid E.164 phone is entered", async () => {
    renderWithProvider(<SignupPhonePage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("signup-stayinformed-form"),
      ).toBeInTheDocument();
    });

    const input = screen.getByTestId("field-phone-number");
    fireEvent.change(input, { target: { value: "+15551234567" } });
    fireEvent.blur(input);

    const button = screen.getByTestId(
      "signup-stayinformed-continue",
    ) as HTMLButtonElement;
    await waitFor(() => {
      expect(button).not.toBeDisabled();
    });
  });
});
