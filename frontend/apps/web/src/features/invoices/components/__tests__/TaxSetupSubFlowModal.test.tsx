/**
 * TaxSetupSubFlowModal unit tests — FE-B22
 *
 * Location: apps/web/src/features/invoices/components/__tests__/TaxSetupSubFlowModal.test.tsx
 *
 * Verifies: opens on 412, shows settings link (no tax endpoint available).
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TaxSetupSubFlowModal } from "../TaxSetupSubFlowModal";

const BASE_PROPS = {
  open: true,
  detail: "Tax rates must be configured before creating invoices.",
  onClose: vi.fn(),
};

describe("TaxSetupSubFlowModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when open=false", () => {
    const { container } = render(
      <TaxSetupSubFlowModal {...BASE_PROPS} open={false} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders when open=true with appropriate message", () => {
    render(<TaxSetupSubFlowModal {...BASE_PROPS} />);
    expect(screen.getByText(/tax configuration required/i)).toBeTruthy();
    expect(
      screen.getByText(
        /tax rates must be configured before creating invoices/i,
      ),
    ).toBeTruthy();
  });

  it("shows link to Settings → Tax page", () => {
    render(<TaxSetupSubFlowModal {...BASE_PROPS} />);
    const taxLink = screen.getByTestId("tax-settings-link");
    expect(taxLink).toBeTruthy();
    expect(taxLink.getAttribute("href")).toBe("/settings/tax");
  });

  it("shows 'Configure Tax' button", () => {
    render(<TaxSetupSubFlowModal {...BASE_PROPS} />);
    expect(screen.getByText("Configure Tax")).toBeTruthy();
  });

  it("Close button calls onClose", () => {
    render(<TaxSetupSubFlowModal {...BASE_PROPS} />);
    fireEvent.click(screen.getByText("Close"));
    expect(BASE_PROPS.onClose).toHaveBeenCalledTimes(1);
  });

  it("shows fallback message when detail is not provided", () => {
    render(
      <TaxSetupSubFlowModal open={true} onClose={vi.fn()} detail={undefined} />,
    );
    expect(
      screen.getByText(
        /tax rates must be configured before creating invoices/i,
      ),
    ).toBeTruthy();
  });
});
