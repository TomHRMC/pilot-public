/**
 * Data & Privacy Page Integration Tests — BETA-B4
 *
 * Location: apps/web/__tests__/batch_beta_v1_b4/data-privacy.test.tsx
 * Route: /settings/data-privacy
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import DataPrivacyPage from "../../src/app/(authed)/settings/data-privacy/page";

// Mock next/link for test environment
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) => <a href={href}>{children}</a>,
}));

describe("DataPrivacyPage (/settings/data-privacy)", () => {
  it("renders without crashing (not 404)", () => {
    const { container } = render(<DataPrivacyPage />);
    expect(container).toBeDefined();
  });

  it("shows Data & Privacy heading", () => {
    render(<DataPrivacyPage />);
    expect(screen.getByText("Data & Privacy")).toBeDefined();
  });

  it("shows data retention section", () => {
    render(<DataPrivacyPage />);
    expect(screen.getByText("Data Retention")).toBeDefined();
  });

  it("shows link to data export page", () => {
    render(<DataPrivacyPage />);
    const link = screen.getByRole("link", { name: /Export Your Data/i });
    expect(link.getAttribute("href")).toBe("/settings/my-account/data-export");
  });

  it("shows retention policy text", () => {
    render(<DataPrivacyPage />);
    expect(screen.getByText(/12 months/i)).toBeDefined();
  });
});
