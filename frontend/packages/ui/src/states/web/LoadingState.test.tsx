/**
 * LoadingState (web) — unit tests
 * Location: packages/ui/src/states/web/LoadingState.test.tsx
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingState } from "./LoadingState";

describe("LoadingState (web)", () => {
  describe("full-page variant", () => {
    it("renders with role='status' and aria-busy='true'", () => {
      render(<LoadingState type="full-page" />);
      const el = screen.getByRole("status");
      expect(el).toBeTruthy();
      expect(el.getAttribute("aria-busy")).toBe("true");
    });

    it("renders default 4 skeleton rows", () => {
      const { container } = render(<LoadingState type="full-page" />);
      const rows = container.querySelectorAll(".animate-pulse");
      expect(rows.length).toBe(4);
    });

    it("renders N skeleton rows when skeletonRows prop provided", () => {
      const { container } = render(
        <LoadingState type="full-page" skeletonRows={6} />,
      );
      const rows = container.querySelectorAll(".animate-pulse");
      expect(rows.length).toBe(6);
    });

    it("renders default loading label via aria-label attribute", () => {
      const { container } = render(<LoadingState type="full-page" />);
      const el = container.querySelector("[aria-label]") as HTMLElement | null;
      expect(el?.getAttribute("aria-label")).toBe("Loading\u2026");
    });

    it("renders custom label via aria-label attribute when provided", () => {
      const { container } = render(
        <LoadingState type="full-page" label={"Fetching data\u2026"} />,
      );
      const el = container.querySelector("[aria-label]") as HTMLElement | null;
      expect(el?.getAttribute("aria-label")).toBe("Fetching data\u2026");
    });

    it("applies testID when provided", () => {
      const { container } = render(
        <LoadingState type="full-page" testID="my-loader" />,
      );
      expect(container.querySelector('[data-testid="my-loader"]')).toBeTruthy();
    });
  });

  describe("inline variant", () => {
    it("renders with role='status' and aria-live='polite'", () => {
      render(<LoadingState type="inline" />);
      const el = screen.getByRole("status");
      expect(el.getAttribute("aria-live")).toBe("polite");
    });

    it("renders label via aria-label attribute on status element", () => {
      const { container } = render(
        <LoadingState type="inline" label={"Saving\u2026"} />,
      );
      const el = container.querySelector("[aria-label]") as HTMLElement | null;
      expect(el?.getAttribute("aria-label")).toBe("Saving\u2026");
    });

    it("renders svg spinner", () => {
      const { container } = render(<LoadingState type="inline" />);
      expect(container.querySelector("svg")).toBeTruthy();
    });
  });

  describe("optimistic variant", () => {
    it("wraps children with aria-busy='true'", () => {
      const { container } = render(
        <LoadingState type="optimistic">
          <span>Child content</span>
        </LoadingState>,
      );
      const wrapper = container.querySelector('[aria-busy="true"]');
      expect(wrapper).toBeTruthy();
    });

    it("renders children inside optimistic wrapper", () => {
      render(
        <LoadingState type="optimistic">
          <span>My content</span>
        </LoadingState>,
      );
      expect(screen.getByText("My content")).toBeTruthy();
    });

    it("applies animate-pulse class to optimistic wrapper", () => {
      const { container } = render(
        <LoadingState type="optimistic">
          <span>content</span>
        </LoadingState>,
      );
      expect(container.querySelector(".animate-pulse")).toBeTruthy();
    });
  });
});
