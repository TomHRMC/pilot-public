/**
 * Signup Wizard — Integration Tests (Phase 4)
 * Location: apps/web/__tests__/batch_fe_b13/signup-wizard.integration.test.tsx
 *
 * Tests the critical paths for RULE 7, RULE 4, and key wizard scenarios.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// C-B5: OnboardingChecklistWidget now uses useRouter for messaging setup navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

// ─── Test Helpers ──────────────────────────────────────────────────────────

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={createQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

// ─── Checklist Widget Tests ────────────────────────────────────────────────

import { OnboardingChecklistWidget } from "../../src/features/onboarding/components/OnboardingChecklistWidget";
import type { OnboardingChecklistState } from "../../src/features/onboarding/types";

const COMPLETE_CHECKLIST: OnboardingChecklistState = {
  tenantId: "test-tenant-001",
  accountCreated: true,
  legalAccepted: true,
  tierSelected: true,
  firstCustomerAdded: true,
  firstCustomerAddedAt: new Date().toISOString(),
  catalogSetup: true,
  catalogSetupAt: new Date().toISOString(),
  messagingSetup: true,
  quickbooksConnected: false,
  quickbooksSkipped: true,
  calendarConnected: false,
  calendarSkipped: true,
  teamInvited: false,
  teamSkipped: true,
  checklistHidden: false,
  checklistDismissedPermanently: false,
};

const INITIAL_CHECKLIST: OnboardingChecklistState = {
  tenantId: "test-tenant-001",
  accountCreated: true,
  legalAccepted: true,
  tierSelected: true,
  firstCustomerAdded: false,
  firstCustomerAddedAt: null,
  catalogSetup: false,
  catalogSetupAt: null,
  messagingSetup: false,
  quickbooksConnected: false,
  quickbooksSkipped: false,
  calendarConnected: false,
  calendarSkipped: false,
  teamInvited: false,
  teamSkipped: false,
  checklistHidden: false,
  checklistDismissedPermanently: false,
};

describe("OnboardingChecklistWidget — integration", () => {
  it("renders checklist with 3 auto-complete items checked on fresh dashboard load", () => {
    render(
      <OnboardingChecklistWidget
        tenantId="test-tenant-001"
        checklistState={INITIAL_CHECKLIST}
      />,
      { wrapper },
    );

    const widget = screen.getByTestId("checklist-widget");
    expect(widget).toBeTruthy();
    // account_created, legal_accepted, tier_selected should show as complete
    expect(screen.getByTestId("checklist-check-accountCreated")).toBeTruthy();
    expect(screen.getByTestId("checklist-check-legalAccepted")).toBeTruthy();
    expect(screen.getByTestId("checklist-check-tierSelected")).toBeTruthy();
  });

  it("widget does NOT render when checklistDismissedPermanently=true", () => {
    render(
      <OnboardingChecklistWidget
        tenantId="test-tenant-001"
        checklistState={{
          ...INITIAL_CHECKLIST,
          checklistDismissedPermanently: true,
        }}
      />,
      { wrapper },
    );

    expect(screen.queryByTestId("checklist-widget")).toBeNull();
  });

  it("widget does NOT render when all items are complete or skipped", () => {
    render(
      <OnboardingChecklistWidget
        tenantId="test-tenant-001"
        checklistState={COMPLETE_CHECKLIST}
      />,
      { wrapper },
    );

    expect(screen.queryByTestId("checklist-widget")).toBeNull();
  });

  it("widget collapses to pill when checklistHidden=true", () => {
    render(
      <OnboardingChecklistWidget
        tenantId="test-tenant-001"
        checklistState={{ ...INITIAL_CHECKLIST, checklistHidden: true }}
      />,
      { wrapper },
    );

    expect(screen.getByTestId("checklist-widget-pill")).toBeTruthy();
    expect(screen.queryByTestId("checklist-widget")).toBeNull();
  });

  it("skippable items render a Skip link", () => {
    render(
      <OnboardingChecklistWidget
        tenantId="test-tenant-001"
        checklistState={INITIAL_CHECKLIST}
      />,
      { wrapper },
    );

    // quickbooks, calendar, team are skippable
    expect(
      screen.getByTestId("checklist-skip-quickbooksConnected"),
    ).toBeTruthy();
    expect(screen.getByTestId("checklist-skip-calendarConnected")).toBeTruthy();
    expect(screen.getByTestId("checklist-skip-teamInvited")).toBeTruthy();
  });

  it("non-skippable items (firstCustomerAdded, catalogSetup) do NOT show Skip link", () => {
    render(
      <OnboardingChecklistWidget
        tenantId="test-tenant-001"
        checklistState={INITIAL_CHECKLIST}
      />,
      { wrapper },
    );

    expect(
      screen.queryByTestId("checklist-skip-firstCustomerAdded"),
    ).toBeNull();
    expect(screen.queryByTestId("checklist-skip-catalogSetup")).toBeNull();
  });

  it("progress counter shows N of 8 done", () => {
    render(
      <OnboardingChecklistWidget
        tenantId="test-tenant-001"
        checklistState={INITIAL_CHECKLIST}
      />,
      { wrapper },
    );

    // 3 auto-complete items done, 0 skipped
    // C-B5: CHECKLIST_ITEMS now has 9 items (messagingSetup added)
    expect(screen.getByText(/3 of 9 tasks done/i)).toBeTruthy();
  });
});

// ─── Trial Status Tests ────────────────────────────────────────────────────

import { TrialExpiryBanner } from "../../src/features/onboarding/components/TrialExpiryBanner";

describe("TrialExpiryBanner", () => {
  it("renders with correct day count for 7 days remaining (alert-600 class)", () => {
    const onUpgradeClick = () => {};
    render(
      <TrialExpiryBanner daysRemaining={7} onUpgradeClick={onUpgradeClick} />,
    );
    const banner = screen.getByTestId("trial-expiry-banner");
    expect(banner).toBeTruthy();
    expect(banner.textContent).toContain("7");
    // Should use alert tokens (not fault) for > 1 day remaining
    expect(banner.className).toContain("alert");
  });

  it("renders with fault-600 class for 1 day remaining (urgent)", () => {
    const onUpgradeClick = () => {};
    render(
      <TrialExpiryBanner daysRemaining={1} onUpgradeClick={onUpgradeClick} />,
    );
    const banner = screen.getByTestId("trial-expiry-banner");
    expect(banner.className).toContain("fault");
  });

  it("does NOT render when daysRemaining > 7", () => {
    const onUpgradeClick = () => {};
    render(
      <TrialExpiryBanner daysRemaining={14} onUpgradeClick={onUpgradeClick} />,
    );
    expect(screen.queryByTestId("trial-expiry-banner")).toBeNull();
  });

  it("'Upgrade now' button calls onUpgradeClick", () => {
    let clicked = false;
    render(
      <TrialExpiryBanner
        daysRemaining={3}
        onUpgradeClick={() => {
          clicked = true;
        }}
      />,
    );
    fireEvent.click(screen.getByTestId("trial-banner-upgrade-button"));
    expect(clicked).toBe(true);
  });

  it("dismisses banner on close button click", () => {
    render(<TrialExpiryBanner daysRemaining={3} onUpgradeClick={() => {}} />);
    expect(screen.getByTestId("trial-expiry-banner")).toBeTruthy();
    fireEvent.click(screen.getByTestId("trial-banner-dismiss"));
    expect(screen.queryByTestId("trial-expiry-banner")).toBeNull();
  });
});

// ─── useTrialStatus hook tests ─────────────────────────────────────────────

import { useTrialStatus } from "../../src/features/onboarding/hooks/useTrialStatus";

describe("useTrialStatus", () => {
  it("returns isOnTrial=false for non-trial tenants", () => {
    const result = useTrialStatus({ is_on_trial: false });
    expect(result.isOnTrial).toBe(false);
    expect(result.daysRemaining).toBe(0);
    expect(result.isExpired).toBe(false);
  });

  it("returns daysRemaining=7 for tenant with 7 days left", () => {
    const trialEndsAt = new Date(
      Date.now() + 7 * 24 * 60 * 60 * 1000,
    ).toISOString();
    const result = useTrialStatus({
      is_on_trial: true,
      trial_ends_at: trialEndsAt,
      trial_expired: false,
    });
    // Should be exactly 7 (ceiling of ≤7 days)
    expect(result.daysRemaining).toBeGreaterThanOrEqual(6);
    expect(result.daysRemaining).toBeLessThanOrEqual(8);
    expect(result.isExpired).toBe(false);
    expect(result.showSoftGate).toBe(true);
  });

  it("returns isExpired=true when trial_expired=true", () => {
    const result = useTrialStatus({
      is_on_trial: true,
      trial_ends_at: new Date(Date.now() - 1000).toISOString(),
      trial_expired: true,
    });
    expect(result.isExpired).toBe(true);
  });

  it("returns showSoftGate=false for > 7 days remaining", () => {
    const trialEndsAt = new Date(
      Date.now() + 14 * 24 * 60 * 60 * 1000,
    ).toISOString();
    const result = useTrialStatus({
      is_on_trial: true,
      trial_ends_at: trialEndsAt,
      trial_expired: false,
    });
    expect(result.showSoftGate).toBe(false);
  });

  it("returns isOnTrial=false for null tenant", () => {
    const result = useTrialStatus(null);
    expect(result.isOnTrial).toBe(false);
  });
});
