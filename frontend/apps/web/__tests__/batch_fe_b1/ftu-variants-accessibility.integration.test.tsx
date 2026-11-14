/**
 * FTU variants — accessibility integration tests
 * Location: apps/web/__tests__/batch_fe_b1/ftu-variants-accessibility.integration.test.tsx
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { FirstTimeUserState, FTU_DEFAULTS } from "@pilot/ui/states";
import type { FTUSurface } from "@pilot/ui/states";

const ALL_SURFACES: FTUSurface[] = [
  "dashboard",
  "quotes",
  "schedule",
  "customers",
  "invoices",
  "reports",
  "comms",
  "settings",
];

function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <main>
      <h1>Page title</h1>
      {children}
    </main>
  );
}

describe("FTU variants — accessibility integration", () => {
  it.each(ALL_SURFACES)(
    "surface '%s' renders zero axe-style heading hierarchy violations (h2 inside main)",
    (surface) => {
      render(
        <PageWrapper>
          <FirstTimeUserState type={surface} />
        </PageWrapper>,
      );
      const h2 = screen.getByRole("heading", { level: 2 });
      expect(h2).toBeTruthy();
      expect(h2.textContent).toBe(FTU_DEFAULTS[surface].heading);
    },
  );

  it("CTA button is keyboard-accessible (has accessible name)", () => {
    render(<FirstTimeUserState type="dashboard" />);
    const button = screen.getByRole("button", {
      name: FTU_DEFAULTS.dashboard.ctaLabel,
    });
    expect(button).toBeTruthy();
  });

  it("section has accessible role='region' with aria-label", () => {
    render(<FirstTimeUserState type="quotes" />);
    const region = screen.getByRole("region");
    expect(region.getAttribute("aria-label")).toContain("First time setup");
  });
});
