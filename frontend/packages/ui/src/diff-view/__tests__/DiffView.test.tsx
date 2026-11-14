/**
 * DiffView unit tests (web)
 *
 * Location: packages/ui/src/diff-view/__tests__/DiffView.test.tsx
 *
 * Target: 15+ tests covering all variants, color tokens, toggle, revert
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { DiffView } from "../web/DiffView";
import type { DiffLineItem, DiffField } from "../types";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

function makeModifiedLine(overrides?: Partial<DiffLineItem>): DiffLineItem {
  return {
    lineItemId: "line-1",
    label: "200A Panel Upgrade",
    customerVisible: true,
    lineChangeType: "modified",
    fields: [
      {
        fieldName: "unit_price_cents",
        label: "Unit Price",
        baseValue: "150000",
        modifiedValue: "175000",
        changeType: "modified",
        pendingEditId: "edit-uuid-1",
      },
    ],
    ...overrides,
  };
}

function makeAddedLine(): DiffLineItem {
  return {
    lineItemId: "line-new",
    label: "New fixture line",
    customerVisible: true,
    lineChangeType: "added",
    fields: [],
  };
}

function makeRemovedLine(): DiffLineItem {
  return {
    lineItemId: "line-old",
    label: "Old service call",
    customerVisible: true,
    lineChangeType: "removed",
    fields: [],
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("DiffView variant='quote-line'", () => {
  it("renders nothing when all lines are unchanged", () => {
    const { container } = render(
      <DiffView
        variant="quote-line"
        lineItems={[
          {
            lineItemId: "line-1",
            label: "Unchanged line",
            customerVisible: true,
            lineChangeType: "unchanged",
            fields: [],
          },
        ]}
      />,
    );
    expect(container.textContent).toContain("No changes to display");
  });

  it("renders amber tokens for modified lines", () => {
    const { container } = render(
      <DiffView
        variant="quote-line"
        lineItems={[makeModifiedLine()]}
        testID="diff-view-test"
      />,
    );
    // The modified line should use alert (amber) token classes
    const content = container.innerHTML;
    expect(content).toContain("bg-alert-50");
    expect(content).toContain("Modified");
  });

  it("renders green tokens for added lines", () => {
    const { container } = render(
      <DiffView variant="quote-line" lineItems={[makeAddedLine()]} />,
    );
    expect(container.innerHTML).toContain("bg-margin-50");
    expect(container.innerHTML).toContain("Added");
  });

  it("renders red tokens for removed lines", () => {
    const { container } = render(
      <DiffView variant="quote-line" lineItems={[makeRemovedLine()]} />,
    );
    expect(container.innerHTML).toContain("bg-fault-50");
    expect(container.innerHTML).toContain("Removed");
  });

  it("does NOT render unchanged lines in the output", () => {
    render(
      <DiffView
        variant="quote-line"
        lineItems={[
          makeModifiedLine(),
          {
            lineItemId: "line-2",
            label: "Unchanged line",
            customerVisible: true,
            lineChangeType: "unchanged",
            fields: [],
          },
        ]}
      />,
    );
    expect(screen.queryByText("Unchanged line")).toBeNull();
    expect(screen.getByText("200A Panel Upgrade")).toBeTruthy();
  });

  it("calls onRevertField with correct pendingEditId", () => {
    const onRevert = vi.fn();
    render(
      <DiffView
        variant="quote-line"
        lineItems={[makeModifiedLine()]}
        onRevertField={onRevert}
      />,
    );
    const revertBtn = screen.getByRole("button", { name: /revert/i });
    fireEvent.click(revertBtn);
    expect(onRevert).toHaveBeenCalledWith("edit-uuid-1");
  });

  it("showToggle=true renders toggle button", () => {
    render(
      <DiffView
        variant="quote-line"
        lineItems={[makeModifiedLine()]}
        showToggle
      />,
    );
    expect(screen.getByRole("button", { name: /hide changes/i })).toBeTruthy();
  });

  it("showToggle: clicking toggle hides/shows diff markers", () => {
    render(
      <DiffView
        variant="quote-line"
        lineItems={[makeModifiedLine()]}
        showToggle
        defaultShowChanges
      />,
    );
    // Initially visible
    expect(screen.getByText("200A Panel Upgrade")).toBeTruthy();

    // Toggle to hide
    const toggle = screen.getByRole("button", { name: /hide changes/i });
    fireEvent.click(toggle);

    // Content hidden
    expect(screen.queryByText("200A Panel Upgrade")).toBeNull();
  });

  it("defaultShowChanges=false renders clean view initially", () => {
    render(
      <DiffView
        variant="quote-line"
        lineItems={[makeModifiedLine()]}
        showToggle
        defaultShowChanges={false}
      />,
    );
    // Diff content hidden initially
    expect(screen.queryByText("200A Panel Upgrade")).toBeNull();
    // Toggle shows "Show changes"
    expect(screen.getByRole("button", { name: /show changes/i })).toBeTruthy();
  });

  it("has accessible aria-label on container", () => {
    render(
      <DiffView
        variant="quote-line"
        lineItems={[makeModifiedLine()]}
        testID="diff-view-aria-test"
      />,
    );
    const container = screen.getByTestId("diff-view-aria-test");
    expect(container.getAttribute("aria-label")).toBe(
      "Quote line item changes",
    );
  });

  it("renders change type badge text (not color-only) for WCAG 1.4.1", () => {
    render(
      <DiffView
        variant="quote-line"
        lineItems={[makeModifiedLine(), makeAddedLine(), makeRemovedLine()]}
      />,
    );
    // Each change type must have text annotation (not color-only per WCAG 1.4.1)
    expect(screen.getAllByText("Modified").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Added").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Removed").length).toBeGreaterThan(0);
  });
});

describe("DiffView variant='calendar-event'", () => {
  const calendarFields: DiffField[] = [
    {
      fieldName: "scheduled_start_at",
      label: "Start Time",
      baseValue: "2025-05-01T09:00:00Z",
      modifiedValue: "2025-05-01T10:00:00Z",
      changeType: "modified",
    },
  ];

  it("renders entity label as section heading", () => {
    render(
      <DiffView
        variant="calendar-event"
        fieldDiffs={calendarFields}
        entityLabel="Johnson Panel Upgrade — April 30"
        testID="calendar-diff"
      />,
    );
    expect(screen.getByText("Johnson Panel Upgrade — April 30")).toBeTruthy();
  });

  it("renders default sideLabels: Pilot and Google Calendar", () => {
    render(
      <DiffView
        variant="calendar-event"
        fieldDiffs={calendarFields}
        entityLabel="Test Event"
      />,
    );
    // "Pilot" appears in both header and per-field side labels
    expect(screen.getAllByText("Pilot").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Google Calendar").length).toBeGreaterThan(0);
  });

  it("renders custom sideLabels when provided", () => {
    render(
      <DiffView
        variant="calendar-event"
        fieldDiffs={calendarFields}
        entityLabel="Test Event"
        sideLabels={{ base: "Our System", modified: "External Cal" }}
      />,
    );
    expect(screen.getAllByText("Our System").length).toBeGreaterThan(0);
    expect(screen.getAllByText("External Cal").length).toBeGreaterThan(0);
  });
});

describe("DiffView variant='qb-entity'", () => {
  it("renders entity label and QuickBooks side label", () => {
    render(
      <DiffView
        variant="qb-entity"
        fieldDiffs={[]}
        entityLabel="Customer: Johnson Electric"
        testID="qb-diff"
      />,
    );
    expect(screen.getByText("Customer: Johnson Electric")).toBeTruthy();
    expect(screen.getByText("QuickBooks")).toBeTruthy();
  });
});

describe("DiffView variant='entity'", () => {
  it("renders entity label without side labels", () => {
    render(
      <DiffView
        variant="entity"
        fieldDiffs={[
          {
            fieldName: "status",
            baseValue: "active",
            modifiedValue: "inactive",
            changeType: "modified",
          },
        ]}
        entityLabel="Time Entry — Mon, 4.5 hrs"
      />,
    );
    expect(screen.getByText("Time Entry — Mon, 4.5 hrs")).toBeTruthy();
    // No side labels rendered
    expect(screen.queryByText("Pilot")).toBeNull();
  });
});
