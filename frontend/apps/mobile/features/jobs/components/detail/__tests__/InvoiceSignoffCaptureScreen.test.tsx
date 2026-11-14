/**
 * InvoiceSignoffCaptureScreen (S2) unit tests
 *
 * Location: apps/mobile/features/jobs/components/detail/__tests__/InvoiceSignoffCaptureScreen.test.tsx
 *
 * Tests:
 *   - Save disabled until all three gates met
 *   - Name input enables gate 1
 *   - Acknowledge toggles gate 2
 *   - Canvas onOK enables gate 3
 *   - Save calls the create hook with the exact input shape
 *   - Success path fires navigation back
 *
 * Note: Mobile tests mock hooks directly — MSW server is not used.
 * The QueryClient cache is pre-populated so useQuery returns data
 * synchronously without async state updates.
 * Save button enabled/disabled is checked via onPress prop (undefined when disabled).
 */

import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  act,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InvoiceSignoffCaptureScreen } from "../InvoiceSignoffCaptureScreen";

// ── Mock expo-router ──────────────────────────────────────────────────────────

const mockBack = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: mockBack, replace: jest.fn() }),
  useLocalSearchParams: () => ({
    jobId: "job-signoff-test-001",
    invoiceId: "invoice-signoff-001",
  }),
}));

// ── Mock @pilot/ui/auth ───────────────────────────────────────────────────────

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({ user: { id: "tech-user-001" } }),
}));

// ── Signoff context fixture ───────────────────────────────────────────────────
// TEST-UPLIFT-1C: Removed banned jest.mock("@pilot/shared-api"). The
// QueryClient cache is pre-populated below so useQuery returns data
// synchronously — no apiClient mock is needed.

const CONTEXT_FIXTURE = {
  job_id: "job-signoff-test-001",
  customer_display_name: "John Smith",
  invoices: [
    {
      invoice_id: "invoice-signoff-001",
      invoice_number: "INV-0042",
      status: "issued",
      total_cents: 125000,
      balance_due_cents: 125000,
      currency: "USD",
      terms_text: "Standard terms apply.",
      active_signoff: null,
    },
  ],
};

// ── Mock react-native-signature-canvas ────────────────────────────────────────

let mockOnOK: ((base64: string) => void) | null = null;
let mockOnEmpty: (() => void) | null = null;

jest.mock("react-native-signature-canvas", () => {
  const React = require("react");
  const { View } = require("react-native");
  return React.forwardRef((_props: any, ref: any) => {
    mockOnOK = _props.onOK ?? null;
    mockOnEmpty = _props.onEmpty ?? null;
    React.useImperativeHandle(ref, () => ({
      clearSignature: jest.fn(),
      getData: jest.fn(() => "iVBORw0KGgo="),
    }));
    return React.createElement(View, { testID: "signoff-canvas" });
  });
});

// ── Mock Vibration + AccessibilityInfo ────────────────────────────────────────
// RN index.js accesses `.default` from these internal modules, so the mock
// must export a default key containing the methods.

jest.mock("react-native/Libraries/Vibration/Vibration", () => ({
  __esModule: true,
  default: { vibrate: jest.fn() },
}));

jest.mock(
  "react-native/Libraries/Components/AccessibilityInfo/AccessibilityInfo",
  () => ({
    __esModule: true,
    default: { announceForAccessibility: jest.fn() },
  }),
);

// ── Mock useCreateInvoiceSignoff ──────────────────────────────────────────────

const mockCreate = jest.fn(async () => ({}));
const mockUseCreateInvoiceSignoff = jest.fn(() => ({
  create: mockCreate,
  isPending: false,
  error: null,
}));

jest.mock("../../../../offline-sync/hooks/useCreateInvoiceSignoff", () => ({
  useCreateInvoiceSignoff: () => mockUseCreateInvoiceSignoff(),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
        gcTime: Infinity,
      },
      mutations: { retry: false },
    },
  });
  // Pre-populate the cache so useQuery returns data synchronously
  qc.setQueryData(
    ["job-signoff-context", "job-signoff-test-001"],
    CONTEXT_FIXTURE,
  );
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

function renderScreen() {
  return render(
    <InvoiceSignoffCaptureScreen
      jobId="job-signoff-test-001"
      invoiceId="invoice-signoff-001"
    />,
    { wrapper: createWrapper() },
  );
}

/** When gates are unmet, the save button is disabled (accessibilityState.disabled = true) */
function expectSaveDisabled() {
  expect(
    screen.getByTestId("signoff-save-button").props.accessibilityState.disabled,
  ).toBe(true);
}

/** When all gates are met, the save button is enabled (accessibilityState.disabled = false) */
function expectSaveEnabled() {
  expect(
    screen.getByTestId("signoff-save-button").props.accessibilityState.disabled,
  ).toBe(false);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("InvoiceSignoffCaptureScreen (S2)", () => {
  beforeEach(() => {
    mockBack.mockClear();
    mockCreate.mockClear();
    mockOnOK = null;
    mockOnEmpty = null;
  });

  it("renders the screen with Save button disabled initially", () => {
    renderScreen();
    expect(screen.getByTestId("signoff-save-button")).toBeTruthy();
    expectSaveDisabled();
  });

  it("enables gate 1 when name is entered", () => {
    renderScreen();

    fireEvent.changeText(
      screen.getByTestId("signoff-name-input"),
      "John Smith",
    );

    // Still disabled — gates 2 and 3 not met
    expectSaveDisabled();
  });

  it("toggles gate 2 when acknowledge is pressed", () => {
    renderScreen();

    fireEvent.press(screen.getByTestId("signoff-acknowledge"));

    // Still disabled — gates 1 and 3 not met
    expectSaveDisabled();
  });

  it("enables gate 3 when canvas onOK fires", () => {
    renderScreen();

    // Enter name (gate 1)
    fireEvent.changeText(
      screen.getByTestId("signoff-name-input"),
      "John Smith",
    );
    // Acknowledge (gate 2)
    fireEvent.press(screen.getByTestId("signoff-acknowledge"));

    // Still disabled — gate 3 not met
    expectSaveDisabled();

    // Fire onOK (gate 3)
    expect(mockOnOK).toBeTruthy();
    act(() => {
      mockOnOK!("iVBORw0KGgo=");
    });

    // Now all gates met — Save enabled
    expectSaveEnabled();
  });

  it("calls create hook with exact input shape on Save", async () => {
    renderScreen();

    // Meet all 3 gates
    fireEvent.changeText(
      screen.getByTestId("signoff-name-input"),
      "John Smith",
    );
    fireEvent.press(screen.getByTestId("signoff-acknowledge"));
    act(() => {
      mockOnOK!("iVBORw0KGgo=");
    });

    await act(async () => {
      fireEvent.press(screen.getByTestId("signoff-save-button"));
    });

    expect(mockCreate).toHaveBeenCalledWith({
      invoiceId: "invoice-signoff-001",
      signedByName: "John Smith",
      termsAcknowledged: true,
      signaturePngBase64: "iVBORw0KGgo=",
      capturedBy: "tech-user-001",
    });
  });

  it("shows success overlay on successful save", async () => {
    renderScreen();

    // Meet all 3 gates
    fireEvent.changeText(
      screen.getByTestId("signoff-name-input"),
      "John Smith",
    );
    fireEvent.press(screen.getByTestId("signoff-acknowledge"));
    act(() => {
      mockOnOK!("iVBORw0KGgo=");
    });

    await act(async () => {
      fireEvent.press(screen.getByTestId("signoff-save-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("signoff-success-overlay")).toBeTruthy();
    });
  });
});
