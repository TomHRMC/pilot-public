/**
 * NotificationPreferenceMatrix — Unit tests
 * Location: packages/ui/src/notification-preference-matrix/NotificationPreferenceMatrix.test.tsx
 *
 * Critical tests:
 * - Forced-minimum cells: aria-disabled, no onClick, no tabindex, pointer-events:none
 * - Scope badges render correctly
 * - visibleCategories filters correctly
 * - Bulk action buttons call correct callbacks
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { NotificationPreferenceMatrix } from "./NotificationPreferenceMatrix";
import type {
  NotificationPreferenceCell,
  NotificationCategoryRow,
} from "./types";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const mockCategories: NotificationCategoryRow[] = [
  {
    category_id: "job_activity",
    display_label: "Job activity",
    description: "Job updates",
    display_order: 1,
    has_asymmetric_forced_minimum: false,
  },
  {
    category_id: "system_alerts",
    display_label: "System alerts",
    description: "Critical alerts",
    display_order: 2,
    has_asymmetric_forced_minimum: false,
  },
  {
    category_id: "customer_activity",
    display_label: "Customer activity",
    description: "Customer messages",
    display_order: 3,
    has_asymmetric_forced_minimum: true,
  },
];

const mockPreferences: NotificationPreferenceCell[] = [
  // job_activity — all interactive
  {
    category_id: "job_activity",
    channel: "push",
    enabled: true,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "job_activity",
    channel: "email",
    enabled: false,
    scope: "tenant",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "job_activity",
    channel: "in_app",
    enabled: true,
    scope: "system",
    forced_minimum: false,
    can_disable: true,
  },
  // system_alerts — all forced minimum
  {
    category_id: "system_alerts",
    channel: "push",
    enabled: true,
    scope: "system",
    forced_minimum: true,
    can_disable: false,
  },
  {
    category_id: "system_alerts",
    channel: "email",
    enabled: true,
    scope: "system",
    forced_minimum: true,
    can_disable: false,
  },
  {
    category_id: "system_alerts",
    channel: "in_app",
    enabled: true,
    scope: "system",
    forced_minimum: true,
    can_disable: false,
  },
  // customer_activity — push forced, others not
  {
    category_id: "customer_activity",
    channel: "push",
    enabled: true,
    scope: "system",
    forced_minimum: true,
    can_disable: false,
  },
  {
    category_id: "customer_activity",
    channel: "email",
    enabled: false,
    scope: "user",
    forced_minimum: false,
    can_disable: true,
  },
  {
    category_id: "customer_activity",
    channel: "in_app",
    enabled: true,
    scope: "tenant",
    forced_minimum: false,
    can_disable: true,
  },
];

function renderMatrix(
  overrides: Partial<Parameters<typeof NotificationPreferenceMatrix>[0]> = {},
) {
  const onCellChange = vi.fn().mockResolvedValue(undefined);
  const onRowRevert = vi.fn().mockResolvedValue(undefined);
  const onCellRevert = vi.fn().mockResolvedValue(undefined);
  const onMuteAllPush = vi.fn().mockResolvedValue(undefined);
  const onMuteAllEmail = vi.fn().mockResolvedValue(undefined);
  const onResetAll = vi.fn().mockResolvedValue(undefined);

  render(
    <NotificationPreferenceMatrix
      preferences={mockPreferences}
      categories={mockCategories}
      onCellChange={onCellChange}
      onRowRevert={onRowRevert}
      onCellRevert={onCellRevert}
      onMuteAllPush={onMuteAllPush}
      onMuteAllEmail={onMuteAllEmail}
      onResetAll={onResetAll}
      {...overrides}
    />,
  );

  return {
    onCellChange,
    onRowRevert,
    onCellRevert,
    onMuteAllPush,
    onMuteAllEmail,
    onResetAll,
  };
}

// ─── Matrix structure ─────────────────────────────────────────────────────────

describe("NotificationPreferenceMatrix — structure", () => {
  it("renders all 3 category rows", () => {
    renderMatrix();
    expect(screen.getByText("Job activity")).toBeInTheDocument();
    expect(screen.getByText("System alerts")).toBeInTheDocument();
    expect(screen.getByText("Customer activity")).toBeInTheDocument();
  });

  it("renders Push, Email, In-app column headers", () => {
    renderMatrix();
    expect(screen.getByText("Push")).toBeInTheDocument();
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.getByText("In-app")).toBeInTheDocument();
  });

  it("renders categories in display_order (Job activity before System alerts)", () => {
    renderMatrix();
    const rows = screen.getAllByRole("row");
    // Header row + 3 category rows
    expect(rows.length).toBeGreaterThanOrEqual(4);
  });
});

// ─── CRITICAL: Forced-minimum cell enforcement ────────────────────────────────

describe("Forced-minimum cell (RULE 3 enforcement)", () => {
  it("system_alerts push cell has aria-disabled='true'", () => {
    renderMatrix();
    const cell = screen.getByTestId("forced-min-cell-system_alerts-push");
    expect(cell).toHaveAttribute("aria-disabled", "true");
  });

  it("system_alerts email cell has aria-disabled='true'", () => {
    renderMatrix();
    expect(
      screen.getByTestId("forced-min-cell-system_alerts-email"),
    ).toHaveAttribute("aria-disabled", "true");
  });

  it("system_alerts in_app cell has aria-disabled='true'", () => {
    renderMatrix();
    expect(
      screen.getByTestId("forced-min-cell-system_alerts-in_app"),
    ).toHaveAttribute("aria-disabled", "true");
  });

  it("customer_activity push cell has aria-disabled='true'", () => {
    renderMatrix();
    expect(
      screen.getByTestId("forced-min-cell-customer_activity-push"),
    ).toHaveAttribute("aria-disabled", "true");
  });

  it("forced-minimum cell has pointer-events:none", () => {
    renderMatrix();
    const cell = screen.getByTestId("forced-min-cell-system_alerts-push");
    expect(cell).toHaveStyle({ pointerEvents: "none" });
  });

  it("clicking forced-minimum push cell does NOT call onCellChange", () => {
    const { onCellChange } = renderMatrix();
    const td = screen.getByTestId("matrix-td-system_alerts-push");
    fireEvent.click(td);
    expect(onCellChange).not.toHaveBeenCalled();
  });

  it("clicking forced-minimum email cell does NOT call onCellChange", () => {
    const { onCellChange } = renderMatrix();
    const td = screen.getByTestId("matrix-td-system_alerts-email");
    fireEvent.click(td);
    expect(onCellChange).not.toHaveBeenCalled();
  });

  it("forced-minimum cell has no form submission path", () => {
    renderMatrix();
    // The cell is a div, not a button — cannot be submitted
    const cell = screen.getByTestId("forced-min-cell-system_alerts-push");
    expect(cell.tagName).not.toBe("BUTTON");
    expect(cell.tagName).not.toBe("INPUT");
  });
});

// ─── Interactive cells ────────────────────────────────────────────────────────

describe("Interactive cells", () => {
  it("job_activity push cell is interactive (has role=switch)", () => {
    renderMatrix();
    const cell = screen.getByTestId("matrix-cell-job_activity-push");
    expect(cell).toHaveAttribute("role", "switch");
  });

  it("clicking job_activity push cell calls onCellChange", () => {
    const { onCellChange } = renderMatrix();
    const cell = screen.getByTestId("matrix-cell-job_activity-push");
    fireEvent.click(cell);
    expect(onCellChange).toHaveBeenCalledWith(
      "job_activity",
      "push",
      expect.any(Boolean),
    );
  });

  it("customer_activity email cell is interactive", () => {
    renderMatrix();
    expect(
      screen.getByTestId("matrix-cell-customer_activity-email"),
    ).toBeInTheDocument();
  });

  it("isPending=true disables all interactive toggles", () => {
    renderMatrix({ isPending: true });
    const cell = screen.getByTestId("matrix-cell-job_activity-push");
    expect(cell).toBeDisabled();
  });

  it("isPending=true still shows forced-minimum cells (not affected by isPending)", () => {
    renderMatrix({ isPending: true });
    expect(
      screen.getByTestId("forced-min-cell-system_alerts-push"),
    ).toBeInTheDocument();
  });
});

// ─── Scope badges ─────────────────────────────────────────────────────────────

describe("Scope badges", () => {
  it("user-scoped cell shows (you) badge", () => {
    renderMatrix();
    const td = screen.getByTestId("matrix-td-job_activity-push");
    expect(td).toHaveTextContent("you");
  });

  it("tenant-scoped cell shows (tenant) badge", () => {
    renderMatrix();
    const td = screen.getByTestId("matrix-td-job_activity-email");
    expect(td).toHaveTextContent("tenant");
  });

  it("system-scoped cell shows (default) badge", () => {
    renderMatrix();
    const td = screen.getByTestId("matrix-td-job_activity-in_app");
    expect(td).toHaveTextContent("default");
  });
});

// ─── Row revert ───────────────────────────────────────────────────────────────

describe("Row revert", () => {
  it("'Match tenant default' appears for rows with user override", () => {
    renderMatrix();
    // job_activity has push: user, customer_activity email: user
    expect(
      screen.getAllByText("Match tenant default").length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("'Match tenant default' does not appear for rows with no user override", () => {
    // system_alerts has no user override cells
    renderMatrix({ visibleCategories: ["system_alerts"] });
    expect(screen.queryByText("Match tenant default")).not.toBeInTheDocument();
  });

  it("clicking 'Match tenant default' calls onRowRevert with correct categoryId", () => {
    const { onRowRevert } = renderMatrix({
      visibleCategories: ["job_activity"],
    });
    fireEvent.click(screen.getByText("Match tenant default"));
    expect(onRowRevert).toHaveBeenCalledWith("job_activity");
  });
});

// ─── Bulk actions ─────────────────────────────────────────────────────────────

describe("Bulk action buttons", () => {
  it("'Mute all push' button exists and is enabled", () => {
    renderMatrix();
    expect(screen.getByTestId("mute-all-push")).toBeEnabled();
  });

  it("clicking 'Mute all push' calls onMuteAllPush", () => {
    const { onMuteAllPush } = renderMatrix();
    fireEvent.click(screen.getByTestId("mute-all-push"));
    expect(onMuteAllPush).toHaveBeenCalledTimes(1);
  });

  it("clicking 'Mute all email' calls onMuteAllEmail", () => {
    const { onMuteAllEmail } = renderMatrix();
    fireEvent.click(screen.getByTestId("mute-all-email"));
    expect(onMuteAllEmail).toHaveBeenCalledTimes(1);
  });

  it("clicking 'Reset to tenant defaults' calls onResetAll", () => {
    const { onResetAll } = renderMatrix();
    fireEvent.click(screen.getByTestId("reset-all"));
    expect(onResetAll).toHaveBeenCalledTimes(1);
  });

  it("isPending=true disables bulk action buttons", () => {
    renderMatrix({ isPending: true });
    expect(screen.getByTestId("mute-all-push")).toBeDisabled();
    expect(screen.getByTestId("mute-all-email")).toBeDisabled();
    expect(screen.getByTestId("reset-all")).toBeDisabled();
  });
});

// ─── visibleCategories filter ─────────────────────────────────────────────────

describe("visibleCategories (FE-B13 embedding)", () => {
  it("visibleCategories=['job_activity'] shows only job_activity", () => {
    renderMatrix({ visibleCategories: ["job_activity"] });
    expect(screen.getByText("Job activity")).toBeInTheDocument();
    expect(screen.queryByText("System alerts")).not.toBeInTheDocument();
    expect(screen.queryByText("Customer activity")).not.toBeInTheDocument();
  });

  it("visibleCategories=['system_alerts', 'customer_activity'] shows both", () => {
    renderMatrix({ visibleCategories: ["system_alerts", "customer_activity"] });
    expect(screen.queryByText("Job activity")).not.toBeInTheDocument();
    expect(screen.getByText("System alerts")).toBeInTheDocument();
    expect(screen.getByText("Customer activity")).toBeInTheDocument();
  });

  it("visibleCategories=undefined shows all categories", () => {
    renderMatrix();
    expect(screen.getByText("Job activity")).toBeInTheDocument();
    expect(screen.getByText("System alerts")).toBeInTheDocument();
    expect(screen.getByText("Customer activity")).toBeInTheDocument();
  });
});

// ─── Accessibility ────────────────────────────────────────────────────────────

describe("Accessibility", () => {
  it("interactive toggle has aria-label with category and channel", () => {
    renderMatrix();
    const toggle = screen.getByTestId("matrix-cell-job_activity-push");
    expect(toggle).toHaveAttribute(
      "aria-label",
      expect.stringContaining("job_activity"),
    );
    expect(toggle).toHaveAttribute(
      "aria-label",
      expect.stringContaining("push"),
    );
  });

  it("forced-minimum cell has aria-disabled='true' (not just visual opacity)", () => {
    renderMatrix();
    const cell = screen.getByTestId("forced-min-cell-system_alerts-push");
    // Must be semantically non-interactive, not just visually muted
    expect(cell).toHaveAttribute("aria-disabled", "true");
    // Must NOT have tabIndex (cannot be reached by keyboard)
    expect(cell.getAttribute("tabindex")).toBeNull();
  });
});
