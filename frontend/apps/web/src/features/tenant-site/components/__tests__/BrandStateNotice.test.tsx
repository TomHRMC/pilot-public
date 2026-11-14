/**
 * BrandStateNotice — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/components/__tests__/BrandStateNotice.test.tsx
 *
 * Tests all 4 state-keyed variants + default fallback.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { BrandStateNotice } from "../BrandStateNotice";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

describe("BrandStateNotice", () => {
  it("renders 'Ready for brand submission' for status=none", () => {
    render(<BrandStateNotice brandStatus="none" />);
    expect(screen.getByText("Ready for brand submission")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("renders 'Ready for brand submission' for status=draft", () => {
    render(<BrandStateNotice brandStatus="draft" />);
    expect(screen.getByText("Ready for brand submission")).toBeInTheDocument();
  });

  it("renders 'Brand registration in progress' for status=in-flight", () => {
    render(<BrandStateNotice brandStatus="in-flight" />);
    expect(
      screen.getByText("Brand registration in progress"),
    ).toBeInTheDocument();
  });

  it("renders 'Brand registration was rejected' for status=brand_rejected", () => {
    render(<BrandStateNotice brandStatus="brand_rejected" />);
    expect(
      screen.getByText("Brand registration was rejected"),
    ).toBeInTheDocument();
  });

  it("renders live brand warning for status=active", () => {
    render(<BrandStateNotice brandStatus="active" />);
    expect(screen.getByText(/Your brand is live/)).toBeInTheDocument();
  });

  it("renders live brand warning for status=approved", () => {
    render(<BrandStateNotice brandStatus="approved" />);
    expect(screen.getByText(/Your brand is live/)).toBeInTheDocument();
  });

  it("renders default variant for unknown status", () => {
    render(<BrandStateNotice brandStatus="unknown-xyz" />);
    expect(screen.getByText("Ready for brand submission")).toBeInTheDocument();
  });

  it("includes deep link to /settings/messaging for none/draft variant", () => {
    render(<BrandStateNotice brandStatus="none" />);
    const link = screen.getByText("Go to Messaging Setup →");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "/settings/messaging");
  });
});
