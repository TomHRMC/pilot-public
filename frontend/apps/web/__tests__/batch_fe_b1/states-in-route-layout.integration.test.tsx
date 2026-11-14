/**
 * States catalog — integration tests in web route layout
 * Location: apps/web/__tests__/batch_fe_b1/states-in-route-layout.integration.test.tsx
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// Import from the package path — resolved via vitest.config.ts alias
import { EmptyState } from "@pilot/ui/states";
import { LoadingState } from "@pilot/ui/states";
import { ErrorState } from "@pilot/ui/states";
import { FirstTimeUserState } from "@pilot/ui/states";
import { FTU_DEFAULTS } from "@pilot/ui/states";

// Simulate a minimal authed layout wrapper (no real Next.js routing needed)
function AuthedLayoutWrapper({ children }: { children: React.ReactNode }) {
  return <main data-testid="authed-layout">{children}</main>;
}

describe("States catalog — integration in web route layout", () => {
  it("EmptyState renders inside layout without breaking layout structure", () => {
    render(
      <AuthedLayoutWrapper>
        <EmptyState type="no-data" />
      </AuthedLayoutWrapper>,
    );
    expect(screen.getByTestId("authed-layout")).toBeTruthy();
    expect(screen.getByRole("region")).toBeTruthy();
  });

  it("LoadingState full-page renders as expected inside layout", () => {
    render(
      <AuthedLayoutWrapper>
        <LoadingState type="full-page" />
      </AuthedLayoutWrapper>,
    );
    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.getByRole("status").getAttribute("aria-busy")).toBe("true");
  });

  it("ErrorState permission renders inside a simulated permission-restricted route", () => {
    render(
      <AuthedLayoutWrapper>
        <ErrorState type="permission" />
      </AuthedLayoutWrapper>,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toBeTruthy();
  });

  it.each([
    "dashboard",
    "quotes",
    "schedule",
    "customers",
    "invoices",
    "reports",
    "comms",
    "settings",
  ] as const)(
    "FirstTimeUserState '%s' renders inside layout without crashing",
    (surface) => {
      render(
        <AuthedLayoutWrapper>
          <FirstTimeUserState type={surface} />
        </AuthedLayoutWrapper>,
      );
      expect(screen.getByText(FTU_DEFAULTS[surface].heading)).toBeTruthy();
    },
  );
});
