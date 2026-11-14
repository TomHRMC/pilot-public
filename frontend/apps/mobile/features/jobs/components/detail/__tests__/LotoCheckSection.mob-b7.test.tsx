/**
 * LotoCheckSection unit tests — MOB-B7 (policy gate)
 *
 * Location: apps/mobile/features/jobs/components/detail/__tests__/LotoCheckSection.mob-b7.test.tsx
 *
 * Tests:
 *   - "Optional" badge shown when loto_confirmation_required = false
 *   - No "Optional" badge when loto_confirmation_required = true
 *   - "Optional" badge shown when useLotoPolicy errors (graceful degradation)
 *   - Section is NEVER hidden regardless of policy
 */

import React from "react";
import { render, screen } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LotoCheckSection } from "../LotoCheckSection";

// ── Mock WatermelonDB ─────────────────────────────────────────────────────────
jest.mock("../../../../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({ create: jest.fn() }),
  },
}));

// ── Mock useConfirmLoto ───────────────────────────────────────────────────────
jest.mock("../../../../offline-sync/hooks/useConfirmLoto", () => ({
  useConfirmLoto: () => ({
    confirm: jest.fn(),
    isPending: false,
  }),
}));

// ── Mock useLotoPolicy — default: optional (false) ───────────────────────────
const mockUseLotoPolicy = jest.fn();

jest.mock("../../../hooks/useLotoPolicy", () => ({
  useLotoPolicy: () => mockUseLotoPolicy(),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

function renderSection(existingConfirmations = []) {
  return render(
    <LotoCheckSection
      jobId="job-loto-test-001"
      existingConfirmations={existingConfirmations}
      testID="loto-check-section"
    />,
    { wrapper },
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("LotoCheckSection — MOB-B7 Policy Gate", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows 'Optional' badge when loto_confirmation_required = false", () => {
    mockUseLotoPolicy.mockReturnValue({
      data: { loto_confirmation_required: false },
    });

    renderSection();

    expect(screen.getByTestId("loto-optional-badge")).toBeTruthy();
    // Section is always visible
    expect(screen.getByTestId("loto-check-section")).toBeTruthy();
    // All three items visible
    expect(screen.getByTestId("loto-item-lockout_points")).toBeTruthy();
    expect(screen.getByTestId("loto-item-de_energized")).toBeTruthy();
    expect(screen.getByTestId("loto-item-tag_placement")).toBeTruthy();
  });

  it("does NOT show 'Optional' badge when loto_confirmation_required = true", () => {
    mockUseLotoPolicy.mockReturnValue({
      data: { loto_confirmation_required: true },
    });

    renderSection();

    // No optional badge in required mode
    expect(screen.queryByTestId("loto-optional-badge")).toBeNull();
    // Section still visible
    expect(screen.getByTestId("loto-check-section")).toBeTruthy();
  });

  it("shows 'Optional' badge when useLotoPolicy errors (graceful degradation)", () => {
    // Error state — data is undefined, defaults to false (optional)
    mockUseLotoPolicy.mockReturnValue({
      data: undefined,
      isError: true,
    });

    renderSection();

    // Graceful degradation: default false → show optional badge
    expect(screen.getByTestId("loto-optional-badge")).toBeTruthy();
    // Section never hidden
    expect(screen.getByTestId("loto-check-section")).toBeTruthy();
  });

  it("never hides the LOTO section regardless of policy", () => {
    // Test with required = true
    mockUseLotoPolicy.mockReturnValue({
      data: { loto_confirmation_required: true },
    });
    const { unmount } = renderSection();
    expect(screen.getByTestId("loto-check-section")).toBeTruthy();
    unmount();

    // Test with required = false
    mockUseLotoPolicy.mockReturnValue({
      data: { loto_confirmation_required: false },
    });
    renderSection();
    expect(screen.getByTestId("loto-check-section")).toBeTruthy();
  });
});
