/**
 * TechFilterPopover — unit tests
 *
 * Location: apps/web/src/features/dispatch-board/components/__tests__/TechFilterPopover.test.tsx
 * DISPATCH-B2
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TechFilterPopover } from "../TechFilterPopover";
import type { DispatchBoardTech } from "../../types-stub";

const MOCK_TECHS: DispatchBoardTech[] = [
  {
    id: "tech-001",
    tech_id: "tech-001",
    name: "Jake Rivera",
    display_color: "#3B43D6",
    avatar_url: null,
  },
  {
    id: "tech-002",
    tech_id: "tech-002",
    name: "Mike Sparks",
    display_color: "#E8724A",
    avatar_url: null,
  },
];

function renderPopover(selectedTechIds: string[] = [], onToggleTech = vi.fn()) {
  return render(
    <TechFilterPopover
      techs={MOCK_TECHS}
      selectedTechIds={selectedTechIds}
      onToggleTech={onToggleTech}
    />,
  );
}

describe("TechFilterPopover", () => {
  it("is closed by default", () => {
    renderPopover();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("opens on trigger button click and aria-expanded flips", () => {
    renderPopover();
    const trigger = screen.getByRole("button", { name: /techs/i });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("menu")).toBeInTheDocument();
  });

  it("closes on Escape key", () => {
    renderPopover();
    fireEvent.click(screen.getByRole("button", { name: /techs/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes on outside mousedown", () => {
    renderPopover();
    fireEvent.click(screen.getByRole("button", { name: /techs/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("shows count badge '· 2' when 2 techs selected", () => {
    renderPopover(["tech-001", "tech-002"]);
    expect(screen.getByText("· 2")).toBeInTheDocument();
  });

  it("does not show count badge when 0 selected", () => {
    renderPopover([]);
    expect(screen.queryByText(/^·/)).not.toBeInTheDocument();
  });

  it("calls onToggleTech with tech id when a checkbox row is clicked", () => {
    const onToggleTech = vi.fn();
    renderPopover([], onToggleTech);
    fireEvent.click(screen.getByRole("button", { name: /techs/i }));
    // Click Jake Rivera checkbox
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(onToggleTech).toHaveBeenCalledWith("tech-001");
  });

  it("all-when-empty: selectedTechIds=[] means every checkbox is checked", () => {
    renderPopover([]);
    fireEvent.click(screen.getByRole("button", { name: /techs/i }));
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    checkboxes.forEach((cb) => {
      expect(cb.checked).toBe(true);
    });
  });

  it("shows specific tech checked when selected, others unchecked", () => {
    renderPopover(["tech-001"]);
    fireEvent.click(screen.getByRole("button", { name: /techs/i }));
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(checkboxes[0].checked).toBe(true); // Jake Rivera
    expect(checkboxes[1].checked).toBe(false); // Mike Sparks
  });
});
