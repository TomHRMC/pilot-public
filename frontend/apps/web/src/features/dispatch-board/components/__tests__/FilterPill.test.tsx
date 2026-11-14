/**
 * FilterPill — unit tests
 *
 * Location: apps/web/src/features/dispatch-board/components/__tests__/FilterPill.test.tsx
 * DISPATCH-B2
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FilterPill } from "../FilterPill";

describe("FilterPill", () => {
  it("renders the label", () => {
    render(<FilterPill label="Scheduled" active={false} onClick={() => {}} />);
    expect(screen.getByText("Scheduled")).toBeInTheDocument();
  });

  it("applies active classes when active=true", () => {
    render(<FilterPill label="Rush" active={true} onClick={() => {}} />);
    const btn = screen.getByRole("button", { name: /rush/i });
    expect(btn.className).toMatch(/bg-white/);
    expect(btn.className).toMatch(/shadow-sm/);
    expect(btn.className).toMatch(/text-neutral-900/);
  });

  it("applies inactive classes when active=false", () => {
    render(<FilterPill label="Rush" active={false} onClick={() => {}} />);
    const btn = screen.getByRole("button", { name: /rush/i });
    expect(btn.className).toMatch(/text-neutral-500/);
    expect(btn.className).not.toMatch(/bg-white/);
  });

  it("fires onClick when clicked", () => {
    const onClick = vi.fn();
    render(<FilterPill label="Standard" active={false} onClick={onClick} />);
    fireEvent.click(screen.getByRole("button", { name: /standard/i }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("renders optional count when provided", () => {
    render(
      <FilterPill label="Tech" active={false} onClick={() => {}} count={5} />,
    );
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("does not render count when not provided", () => {
    const { container } = render(
      <FilterPill label="Tech" active={false} onClick={() => {}} />,
    );
    // Only the label text, no extra count element
    const spans = container.querySelectorAll("span");
    expect(spans).toHaveLength(0);
  });

  it("renders colorDot with aria-hidden when provided", () => {
    const { container } = render(
      <FilterPill
        label="Jake"
        active={false}
        onClick={() => {}}
        colorDot="#3B43D6"
      />,
    );
    const dot = container.querySelector('[aria-hidden="true"]');
    expect(dot).toBeInTheDocument();
    expect((dot as HTMLElement).style.backgroundColor).toBe("rgb(59, 67, 214)");
  });

  it("does not render colorDot when not provided", () => {
    const { container } = render(
      <FilterPill label="Jake" active={false} onClick={() => {}} />,
    );
    const dot = container.querySelector('[aria-hidden="true"]');
    expect(dot).not.toBeInTheDocument();
  });
});
