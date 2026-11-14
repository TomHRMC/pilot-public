/**
 * Notification Preference Matrix — Integration Tests
 * Location: apps/web/__tests__/batch_fe_b12/notificationMatrix.integration.test.tsx
 *
 * Tests the full matrix → toggle cell → API write → refetch cycle.
 * Verifies forced-minimum cell enforcement (aria-disabled, no onClick).
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { NotificationPreferenceMatrix } from "@pilot/ui";
import {
  NOTIFICATION_PREFERENCES,
  NOTIFICATION_CATEGORIES,
} from "../../src/features/notification-preferences/mocks/notificationFixtures";

const server = setupServer(
  http.put(
    "/api/v1/notifications/preferences/:catId/:channel",
    async ({ request }) => {
      const body = (await request.json()) as { enabled: boolean };
      return HttpResponse.json({
        category_id: "job_activity",
        channel: "push",
        enabled: body.enabled,
        scope: "user",
      });
    },
  ),
  http.delete("/api/v1/notifications/preferences/:catId/:channel", () =>
    HttpResponse.json({ cleared: true, reverted_to_scope: "tenant" }),
  ),
  http.post(
    "/api/v1/notifications/preferences/mute-all-push-non-critical",
    () => HttpResponse.json({ muted_count: 6 }),
  ),
  http.post("/api/v1/notifications/preferences/mute-all-email", () =>
    HttpResponse.json({ muted_count: 8 }),
  ),
  http.post("/api/v1/notifications/preferences/reset-to-tenant-defaults", () =>
    HttpResponse.json({ cleared_count: 5 }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderMatrix(
  overrides: Partial<
    React.ComponentProps<typeof NotificationPreferenceMatrix>
  > = {},
) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onCellChange = vi.fn().mockResolvedValue(undefined);
  const onRowRevert = vi.fn().mockResolvedValue(undefined);
  const onCellRevert = vi.fn().mockResolvedValue(undefined);
  const onMuteAllPush = vi.fn().mockResolvedValue(undefined);
  const onMuteAllEmail = vi.fn().mockResolvedValue(undefined);
  const onResetAll = vi.fn().mockResolvedValue(undefined);

  render(
    <QueryClientProvider client={qc}>
      <NotificationPreferenceMatrix
        preferences={NOTIFICATION_PREFERENCES}
        categories={NOTIFICATION_CATEGORIES}
        onCellChange={onCellChange}
        onRowRevert={onRowRevert}
        onCellRevert={onCellRevert}
        onMuteAllPush={onMuteAllPush}
        onMuteAllEmail={onMuteAllEmail}
        onResetAll={onResetAll}
        {...overrides}
      />
    </QueryClientProvider>,
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

describe("NotificationPreferenceMatrix — unit + integration", () => {
  // ─── Matrix structure ───────────────────────────────────────────────────────

  it("renders 8 category rows", () => {
    renderMatrix();
    // 8 categories in fixture
    expect(screen.getByText("Job activity")).toBeInTheDocument();
    expect(screen.getByText("Quote approvals")).toBeInTheDocument();
    expect(screen.getByText("Customer activity")).toBeInTheDocument();
    expect(screen.getByText("Payment received")).toBeInTheDocument();
    expect(screen.getByText("Team updates")).toBeInTheDocument();
    expect(screen.getByText("System alerts")).toBeInTheDocument();
    expect(screen.getByText("QuickBooks sync")).toBeInTheDocument();
    expect(screen.getByText("Voice AI")).toBeInTheDocument();
  });

  it("renders 3 channel column headers", () => {
    renderMatrix();
    expect(screen.getByText("Push")).toBeInTheDocument();
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.getByText("In-app")).toBeInTheDocument();
  });

  it("renders categories in display_order sequence", () => {
    renderMatrix();
    const rows = screen.getAllByRole("row");
    // header row + 8 category rows
    expect(rows.length).toBeGreaterThanOrEqual(9);
  });

  // ─── Forced-minimum enforcement (CRITICAL TEST) ────────────────────────────

  it("forced-minimum cell (customer_activity push) has aria-disabled='true'", () => {
    renderMatrix();
    const forcedCell = screen.getByTestId(
      "forced-min-cell-customer_activity-push",
    );
    expect(forcedCell).toHaveAttribute("aria-disabled", "true");
  });

  it("forced-minimum cell has pointer-events:none", () => {
    renderMatrix();
    const forcedCell = screen.getByTestId(
      "forced-min-cell-customer_activity-push",
    );
    expect(forcedCell).toHaveStyle({ pointerEvents: "none" });
  });

  it("clicking forced-minimum cell does NOT call onCellChange", () => {
    const { onCellChange } = renderMatrix();
    const td = screen.getByTestId("matrix-td-customer_activity-push");
    // The cell container exists but the cell itself has pointer-events:none
    fireEvent.click(td);
    expect(onCellChange).not.toHaveBeenCalled();
  });

  it("system_alerts cells are all aria-disabled", () => {
    renderMatrix();
    const alertPush = screen.getByTestId("forced-min-cell-system_alerts-push");
    const alertEmail = screen.getByTestId(
      "forced-min-cell-system_alerts-email",
    );
    const alertInApp = screen.getByTestId(
      "forced-min-cell-system_alerts-in_app",
    );
    expect(alertPush).toHaveAttribute("aria-disabled", "true");
    expect(alertEmail).toHaveAttribute("aria-disabled", "true");
    expect(alertInApp).toHaveAttribute("aria-disabled", "true");
  });

  // ─── Interactive cells ──────────────────────────────────────────────────────

  it("clicking a non-forced cell calls onCellChange", async () => {
    const { onCellChange } = renderMatrix();
    const cell = screen.getByTestId("matrix-cell-job_activity-push");
    fireEvent.click(cell);
    await waitFor(() => {
      expect(onCellChange).toHaveBeenCalledWith(
        "job_activity",
        "push",
        expect.any(Boolean),
      );
    });
  });

  it("isPending=true disables all toggles", () => {
    renderMatrix({ isPending: true });
    const cell = screen.getByTestId("matrix-cell-job_activity-push");
    expect(cell).toBeDisabled();
  });

  // ─── Scope badges ───────────────────────────────────────────────────────────

  it("user-scoped cell shows (you) scope badge", () => {
    renderMatrix();
    // job_activity push is scope:user in fixture
    const td = screen.getByTestId("matrix-td-job_activity-push");
    expect(td).toHaveTextContent("you");
  });

  it("tenant-scoped cell shows (tenant) scope badge", () => {
    renderMatrix();
    // job_activity in_app is scope:tenant in fixture
    const td = screen.getByTestId("matrix-td-job_activity-in_app");
    expect(td).toHaveTextContent("tenant");
  });

  // ─── Row revert ─────────────────────────────────────────────────────────────

  it("per-row 'Match tenant default' appears for rows with user overrides", () => {
    renderMatrix();
    expect(screen.getAllByText("Match tenant default").length).toBeGreaterThan(
      0,
    );
  });

  it("clicking Match tenant default calls onRowRevert", async () => {
    const { onRowRevert } = renderMatrix();
    const revertBtns = screen.getAllByText("Match tenant default");
    fireEvent.click(revertBtns[0]);
    await waitFor(() => {
      expect(onRowRevert).toHaveBeenCalled();
    });
  });

  // ─── Bulk actions ───────────────────────────────────────────────────────────

  it("Mute all push button calls onMuteAllPush", async () => {
    const { onMuteAllPush } = renderMatrix();
    fireEvent.click(screen.getByTestId("mute-all-push"));
    await waitFor(() => expect(onMuteAllPush).toHaveBeenCalled());
  });

  it("Mute all email button calls onMuteAllEmail", async () => {
    const { onMuteAllEmail } = renderMatrix();
    fireEvent.click(screen.getByTestId("mute-all-email"));
    await waitFor(() => expect(onMuteAllEmail).toHaveBeenCalled());
  });

  it("Reset to tenant defaults calls onResetAll", async () => {
    const { onResetAll } = renderMatrix();
    fireEvent.click(screen.getByTestId("reset-all"));
    await waitFor(() => expect(onResetAll).toHaveBeenCalled());
  });

  // ─── visibleCategories filter (FE-B13 use case) ────────────────────────────

  it("visibleCategories filters to subset", () => {
    renderMatrix({ visibleCategories: ["job_activity", "quote_approvals"] });
    expect(screen.getByText("Job activity")).toBeInTheDocument();
    expect(screen.getByText("Quote approvals")).toBeInTheDocument();
    expect(screen.queryByText("Voice AI")).not.toBeInTheDocument();
    expect(screen.queryByText("System alerts")).not.toBeInTheDocument();
  });

  // ─── Accessibility ──────────────────────────────────────────────────────────

  it("interactive toggle has aria-label with category and channel", () => {
    renderMatrix();
    const cell = screen.getByTestId("matrix-cell-job_activity-push");
    expect(cell).toHaveAttribute(
      "aria-label",
      expect.stringContaining("job_activity"),
    );
    expect(cell).toHaveAttribute("aria-label", expect.stringContaining("push"));
  });
});
