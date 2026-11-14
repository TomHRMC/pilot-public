/**
 * ErrorState (web) — unit tests
 * Location: packages/ui/src/states/web/ErrorState.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorState } from "./ErrorState";
import { ERROR_STATE_DEFAULTS } from "../types";

describe("ErrorState (web)", () => {
  it.each(["network", "server", "validation", "permission"] as const)(
    "renders '%s' type with default title",
    (type) => {
      render(<ErrorState type={type} />);
      expect(screen.getByText(ERROR_STATE_DEFAULTS[type].title)).toBeTruthy();
    },
  );

  it("renders with role='alert'", () => {
    render(<ErrorState type="network" />);
    expect(screen.getByRole("alert")).toBeTruthy();
  });

  it("renders with aria-live='assertive'", () => {
    render(<ErrorState type="server" />);
    const el = screen.getByRole("alert");
    expect(el.getAttribute("aria-live")).toBe("assertive");
  });

  it("renders retry CTA for network type when onRetry provided", () => {
    const onRetry = vi.fn();
    render(<ErrorState type="network" onRetry={onRetry} />);
    fireEvent.click(screen.getByText("Try again"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders retry CTA for server type when onRetry provided", () => {
    const onRetry = vi.fn();
    render(<ErrorState type="server" onRetry={onRetry} />);
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("does NOT render retry CTA for validation type", () => {
    render(<ErrorState type="validation" onRetry={vi.fn()} />);
    expect(screen.queryByText("Try again")).toBeNull();
  });

  it("does NOT render retry CTA for permission type", () => {
    render(<ErrorState type="permission" onRetry={vi.fn()} />);
    expect(screen.queryByText("Try again")).toBeNull();
  });

  it("renders fieldErrors map for validation type", () => {
    render(
      <ErrorState
        type="validation"
        fieldErrors={{ email: "Invalid email address", name: "Required" }}
      />,
    );
    expect(screen.getByText(/Invalid email address/)).toBeTruthy();
    expect(screen.getByText(/Required/)).toBeTruthy();
  });

  it("renders contact support CTA for server type when onContactSupport provided", () => {
    const onContactSupport = vi.fn();
    render(<ErrorState type="server" onContactSupport={onContactSupport} />);
    fireEvent.click(screen.getByText("Contact support"));
    expect(onContactSupport).toHaveBeenCalledTimes(1);
  });

  it("overrides title via title prop", () => {
    render(<ErrorState type="network" title="Custom error title" />);
    expect(screen.getByText("Custom error title")).toBeTruthy();
  });

  it("applies testID when provided", () => {
    const { container } = render(
      <ErrorState type="network" testID="my-error" />,
    );
    expect(container.querySelector('[data-testid="my-error"]')).toBeTruthy();
  });
});
