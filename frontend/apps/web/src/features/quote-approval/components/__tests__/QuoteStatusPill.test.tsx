/**
 * QuoteStatusPill unit tests
 *
 * Location: apps/web/src/features/quote-approval/components/__tests__/QuoteStatusPill.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect } from "vitest";
import { QuoteStatusPill } from "../QuoteStatusPill";

describe("QuoteStatusPill", () => {
  it("renders correct label for pending_approval", () => {
    render(<QuoteStatusPill status="pending_approval" />);
    expect(screen.getByText("Pending Approval")).toBeTruthy();
  });

  it("renders correct label for approved", () => {
    render(<QuoteStatusPill status="approved" />);
    expect(screen.getByText("Approved")).toBeTruthy();
  });

  it("renders correct label for rejected", () => {
    render(<QuoteStatusPill status="rejected" />);
    expect(screen.getByText("Rejected")).toBeTruthy();
  });

  it("renders correct label for draft", () => {
    render(<QuoteStatusPill status="draft" />);
    expect(screen.getByText("Draft")).toBeTruthy();
  });

  it("uses amber token for pending_approval", () => {
    const { container } = render(<QuoteStatusPill status="pending_approval" />);
    expect(container.innerHTML).toContain("bg-alert-100");
    expect(container.innerHTML).toContain("text-alert-800");
  });

  it("uses green token for approved", () => {
    const { container } = render(<QuoteStatusPill status="approved" />);
    expect(container.innerHTML).toContain("bg-margin-100");
  });

  it("uses red token for rejected", () => {
    const { container } = render(<QuoteStatusPill status="rejected" />);
    expect(container.innerHTML).toContain("bg-fault-100");
  });

  it("renders accessibility label", () => {
    render(<QuoteStatusPill status="approved" />);
    const el = screen.getByLabelText(/status: approved/i);
    expect(el).toBeTruthy();
  });
});
