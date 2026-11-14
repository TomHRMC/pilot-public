/**
 * PilotPaginator unit tests — UI-FIX-1C
 *
 * Location: apps/web/src/components/__tests__/PilotPaginator.test.tsx
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { PilotPaginator } from "../PilotPaginator";

describe("PilotPaginator", () => {
  it("renders nothing when total <= limit (single page)", () => {
    const { container } = render(
      <PilotPaginator
        total={10}
        limit={25}
        offset={0}
        onPageChange={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when total equals limit exactly", () => {
    const { container } = render(
      <PilotPaginator
        total={25}
        limit={25}
        offset={0}
        onPageChange={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders correct page count (10 items, limit 5 = Page 1 of 2)", () => {
    render(
      <PilotPaginator total={10} limit={5} offset={0} onPageChange={vi.fn()} />,
    );
    expect(screen.getByTestId("pilot-paginator")).toBeInTheDocument();
    // "of 2" is rendered as separate text nodes — use regex or check max attr
    expect(screen.getByLabelText("Page number")).toHaveAttribute("max", "2");
    const input = screen.getByLabelText("Page number") as HTMLInputElement;
    expect(input.value).toBe("1");
  });

  it("clicking next page calls onPageChange with correct offset", () => {
    const onPageChange = vi.fn();
    render(
      <PilotPaginator
        total={100}
        limit={25}
        offset={0}
        onPageChange={onPageChange}
      />,
    );
    fireEvent.click(screen.getByLabelText("Next page"));
    expect(onPageChange).toHaveBeenCalledWith(25);
  });

  it("clicking previous page calls onPageChange with correct offset", () => {
    const onPageChange = vi.fn();
    render(
      <PilotPaginator
        total={100}
        limit={25}
        offset={25}
        onPageChange={onPageChange}
      />,
    );
    fireEvent.click(screen.getByLabelText("Previous page"));
    expect(onPageChange).toHaveBeenCalledWith(0);
  });

  it("clicking first page (<<) goes to offset 0", () => {
    const onPageChange = vi.fn();
    render(
      <PilotPaginator
        total={100}
        limit={25}
        offset={75}
        onPageChange={onPageChange}
      />,
    );
    fireEvent.click(screen.getByLabelText("First page"));
    expect(onPageChange).toHaveBeenCalledWith(0);
  });

  it("clicking last page (>>) goes to the last page offset", () => {
    const onPageChange = vi.fn();
    render(
      <PilotPaginator
        total={100}
        limit={25}
        offset={0}
        onPageChange={onPageChange}
      />,
    );
    // 100 items, 25 per page: last page offset = floor(99/25)*25 = 75
    fireEvent.click(screen.getByLabelText("Last page"));
    expect(onPageChange).toHaveBeenCalledWith(75);
  });

  it("first and previous buttons are disabled at first page", () => {
    render(
      <PilotPaginator
        total={100}
        limit={25}
        offset={0}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("First page")).toBeDisabled();
    expect(screen.getByLabelText("Previous page")).toBeDisabled();
    expect(screen.getByLabelText("Next page")).not.toBeDisabled();
    expect(screen.getByLabelText("Last page")).not.toBeDisabled();
  });

  it("next and last buttons are disabled at last page", () => {
    render(
      <PilotPaginator
        total={100}
        limit={25}
        offset={75}
        onPageChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Next page")).toBeDisabled();
    expect(screen.getByLabelText("Last page")).toBeDisabled();
    expect(screen.getByLabelText("First page")).not.toBeDisabled();
    expect(screen.getByLabelText("Previous page")).not.toBeDisabled();
  });

  it("typing page number + Enter jumps to that page", () => {
    const onPageChange = vi.fn();
    render(
      <PilotPaginator
        total={100}
        limit={25}
        offset={0}
        onPageChange={onPageChange}
      />,
    );
    const input = screen.getByLabelText("Page number");
    fireEvent.change(input, { target: { value: "3" } });
    fireEvent.keyDown(input, { key: "Enter" });
    // Page 3 = offset 50
    expect(onPageChange).toHaveBeenCalledWith(50);
  });

  it("typing invalid page number + Enter does not call onPageChange", () => {
    const onPageChange = vi.fn();
    render(
      <PilotPaginator
        total={100}
        limit={25}
        offset={0}
        onPageChange={onPageChange}
      />,
    );
    const input = screen.getByLabelText("Page number");
    fireEvent.change(input, { target: { value: "99" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onPageChange).not.toHaveBeenCalled();
  });
});
