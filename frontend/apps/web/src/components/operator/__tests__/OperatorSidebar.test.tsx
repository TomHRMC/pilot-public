/**
 * OperatorSidebar unit tests
 *
 * Location: apps/web/src/components/operator/__tests__/OperatorSidebar.test.tsx
 *
 * C-B15 Part B: nav items render, placeholder is aria-disabled, collapse toggle works.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { OperatorSidebar } from "../OperatorSidebar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/operator/cohort",
}));

// Mock localStorage for useSidebarState
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

describe("OperatorSidebar", () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders nav with aria-label 'Operator navigation'", () => {
    render(<OperatorSidebar />);
    expect(
      screen.getByRole("navigation", { name: "Operator navigation" }),
    ).toBeInTheDocument();
  });

  it("renders Cohort Dashboard nav item", () => {
    render(<OperatorSidebar />);
    expect(
      screen.getByRole("link", { name: "Cohort Dashboard" }),
    ).toBeInTheDocument();
  });

  it("renders More operator tools placeholder with aria-disabled", () => {
    render(<OperatorSidebar />);
    const placeholder = screen.getByText(/More operator tools/i);
    expect(placeholder).toBeInTheDocument();
    expect(placeholder.closest("div")).toHaveAttribute("aria-disabled", "true");
  });

  it("marks Cohort Dashboard as current page (aria-current)", () => {
    render(<OperatorSidebar />);
    const link = screen.getByRole("link", { name: "Cohort Dashboard" });
    expect(link).toHaveAttribute("aria-current", "page");
  });

  it("collapse toggle changes aria-label", async () => {
    const user = userEvent.setup();
    render(<OperatorSidebar />);

    const toggle = screen.getByRole("button", {
      name: "Collapse navigation",
    });
    await user.click(toggle);

    expect(
      screen.getByRole("button", { name: "Expand navigation" }),
    ).toBeInTheDocument();
  });
});
