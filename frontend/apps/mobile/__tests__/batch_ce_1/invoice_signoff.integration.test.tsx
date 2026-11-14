/**
 * CE-1 Part B Integration Test — Invoice Sign-Off full flow
 *
 * Location: apps/mobile/__tests__/batch_ce_1/invoice_signoff.integration.test.tsx
 *
 * Tests:
 *   - Job detail renders the InvoiceSignoffSection with mocked data
 *   - Capture screen renders
 *   - Full save flow enqueues the mutation (assert create hook called
 *     with correct input shape)
 *
 * Note: Mobile tests mock hooks directly — MSW server is not used.
 * The QueryClient cache is pre-populated so useQuery returns data
 * synchronously without async state updates.
 *
 * Per batch-ce-1-react-native-engr-prompt.md Step 7 (integration tests).
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
import { InvoiceSignoffSection } from "../../features/jobs/components/detail/InvoiceSignoffSection";
import { InvoiceSignoffCaptureScreen } from "../../features/jobs/components/detail/InvoiceSignoffCaptureScreen";

// ── Mock expo-router ──────────────────────────────────────────────────────────

const mockPush = jest.fn();
const mockBack = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack, replace: jest.fn() }),
  useLocalSearchParams: () => ({
    jobId: "job-signoff-test-001",
    invoiceId: "invoice-signoff-001",
  }),
  router: { push: mockPush, back: mockBack },
  Link: ({ children }: { children: React.ReactNode }) => children,
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

// ── Mock WatermelonDB ─────────────────────────────────────────────────────────

jest.mock("../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn(() => ({
      query: jest.fn(() => ({ fetch: jest.fn(async () => []) })),
      create: jest.fn((fn: (record: unknown) => void) => {
        const record = {
          id: "mock-signoff-id",
          localSyncStatus: "pending",
          idempotencyKey: "test-idempotency-key",
          clientCaptureAt: new Date(),
          invoiceId: "invoice-signoff-001",
          signedByName: "John Smith",
        };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));

// ── Mock react-native-signature-canvas ────────────────────────────────────────

let mockOnOK: ((base64: string) => void) | null = null;

jest.mock("react-native-signature-canvas", () => {
  const React = require("react");
  const { View } = require("react-native");
  return React.forwardRef((_props: any, ref: any) => {
    mockOnOK = _props.onOK ?? null;
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

jest.mock("../../features/offline-sync/hooks/useCreateInvoiceSignoff", () => ({
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

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CE-1 Part B — Invoice Sign-Off Integration", () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockBack.mockClear();
    mockCreate.mockClear();
    mockOnOK = null;
  });

  it("job detail renders the InvoiceSignoffSection with data", () => {
    render(
      <InvoiceSignoffSection
        jobId="job-signoff-test-001"
        userId="tech-user-001"
        testID="section-invoice-signoff"
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByTestId("section-invoice-signoff")).toBeTruthy();
    // Section should show the ready-to-capture state with invoice data
    expect(screen.getByTestId("signoff-section-ready")).toBeTruthy();
    expect(screen.getByText("INV-0042")).toBeTruthy();
  });

  it("capture screen renders and does not crash", () => {
    render(
      <InvoiceSignoffCaptureScreen
        jobId="job-signoff-test-001"
        invoiceId="invoice-signoff-001"
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByTestId("signoff-capture-screen")).toBeTruthy();
    expect(screen.getByTestId("signoff-save-button")).toBeTruthy();
    expect(screen.getByTestId("signoff-name-input")).toBeTruthy();
    expect(screen.getByTestId("signoff-canvas")).toBeTruthy();
  });

  it("full save flow enqueues the mutation with correct input shape", async () => {
    render(
      <InvoiceSignoffCaptureScreen
        jobId="job-signoff-test-001"
        invoiceId="invoice-signoff-001"
      />,
      { wrapper: createWrapper() },
    );

    // Meet all 3 gates
    fireEvent.changeText(
      screen.getByTestId("signoff-name-input"),
      "John Smith",
    );
    fireEvent.press(screen.getByTestId("signoff-acknowledge"));
    act(() => {
      mockOnOK!("iVBORw0KGgo=");
    });

    // Wait for Save to be enabled (accessibilityState.disabled = false)
    await waitFor(() => {
      expect(
        screen.getByTestId("signoff-save-button").props.accessibilityState
          .disabled,
      ).toBe(false);
    });

    // Press Save
    await act(async () => {
      fireEvent.press(screen.getByTestId("signoff-save-button"));
    });

    // The create hook should have been called with the exact input shape
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        invoiceId: "invoice-signoff-001",
        signedByName: "John Smith",
        termsAcknowledged: true,
        signaturePngBase64: "iVBORw0KGgo=",
        capturedBy: "tech-user-001",
      });
    });

    // Success overlay should appear
    await waitFor(() => {
      expect(screen.getByTestId("signoff-success-overlay")).toBeTruthy();
    });
  });
});
