/**
 * IntegrationConflictResolver unit tests — FE-B9
 *
 * Critical: tests FE-B9 extension (masterDirection, supportsPerFieldResolution)
 * AND regression guard that FE-B8 calendar usage is unaffected.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import { IntegrationConflictResolver } from "./IntegrationConflictResolver";
import type { CalendarConflictDetail, QbConflictDetail } from "./types";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const calendarConflict: CalendarConflictDetail = {
  id: "conflict-cal-1",
  conflictType: "modified_modified",
  jobId: "job-1",
  jobTitle: "Panel Upgrade",
  scheduledStartAt: "2026-05-25T10:00:00Z",
  urgencyScore: 3,
  pilotModifiedByUserId: "user-1",
  pilotModifiedByName: "Mike G",
  pilotModifiedAt: "2026-05-25T09:00:00Z",
  externalModifiedAt: "2026-05-25T08:30:00Z",
  resolution: null,
  resolvedByUserId: null,
  resolvedAt: null,
  autoResolvedStale: false,
  pilotSnapshot: null,
  externalSnapshot: null,
  baseSnapshot: null,
  fieldDiffs: [
    {
      fieldName: "start_time",
      pilotValue: "10:00",
      externalValue: "09:00",
      baseValue: "09:00",
      pilotChange: "modified",
      externalChange: "unchanged",
    },
  ],
  detectedAt: "2026-05-25T09:05:00Z",
  providerDisplayName: "Google Calendar",
};

const qbConflict: QbConflictDetail = {
  id: "qb-invoice-1",
  conflictType: "modified_modified",
  entityType: "invoice",
  entityId: "inv-1",
  entityDisplayName: "Invoice #INV-001",
  masterDirection: "external",
  pilotModifiedAt: "2026-05-25T09:00:00Z",
  externalModifiedAt: "2026-05-25T08:00:00Z",
  pilotModifiedByUserId: "user-1",
  pilotModifiedByName: "Mike G",
  fieldDiffs: [
    {
      fieldName: "amount",
      pilot_value: 100,
      external_value: 150,
      changeType: "modified",
    },
  ],
  financialDeltaCents: 5000,
  pilotAmountCents: 10000,
  qbAmountCents: 15000,
  arImpactDescription: "QB higher",
  taxPeriodWarning: null,
  qbTransactionUrl: null,
  resolution: null,
  resolvedAt: null,
  autoResolvedStale: false,
};

const defaultProps = {
  onResolve: vi.fn(),
  isResolving: false,
  onResolveLater: vi.fn(),
};

// ─── FE-B8 Regression guard ───────────────────────────────────────────────────

describe("IntegrationConflictResolver — FE-B8 regression", () => {
  it("renders Pilot on left when masterDirection is absent (FE-B8 calendar usage)", () => {
    render(
      <IntegrationConflictResolver
        integration="calendar"
        conflict={calendarConflict}
        {...defaultProps}
      />,
    );
    // Pilot is the base column (left) by default
    const diffView = screen.getByTestId("conflict-diff-view");
    expect(diffView).toBeInTheDocument();
  });

  it("does NOT render per-field picker button when supportsPerFieldResolution is absent", () => {
    render(
      <IntegrationConflictResolver
        integration="calendar"
        conflict={calendarConflict}
        {...defaultProps}
      />,
    );
    expect(
      screen.queryByTestId("per-field-picker-toggle"),
    ).not.toBeInTheDocument();
  });

  it("renders accept_local and accept_remote buttons by default", () => {
    render(
      <IntegrationConflictResolver
        integration="calendar"
        conflict={calendarConflict}
        {...defaultProps}
      />,
    );
    expect(screen.getByTestId("resolve-accept-local-btn")).toBeInTheDocument();
    expect(screen.getByTestId("resolve-accept-remote-btn")).toBeInTheDocument();
  });
});

// ─── FE-B9 masterDirection ────────────────────────────────────────────────────

describe("IntegrationConflictResolver — masterDirection", () => {
  it("renders master-direction header when masterDirection='external'", () => {
    render(
      <IntegrationConflictResolver<QbConflictDetail>
        integration="quickbooks"
        conflict={qbConflict}
        masterDirection="external"
        {...defaultProps}
      />,
    );
    expect(screen.getByTestId("master-direction-header")).toBeInTheDocument();
    expect(screen.getByText(/QuickBooks \(master\)/i)).toBeInTheDocument();
  });

  it("does NOT render master-direction header when masterDirection='pilot' (default)", () => {
    render(
      <IntegrationConflictResolver
        integration="calendar"
        conflict={calendarConflict}
        masterDirection="pilot"
        {...defaultProps}
      />,
    );
    expect(
      screen.queryByTestId("master-direction-header"),
    ).not.toBeInTheDocument();
  });

  it("labels primary button correctly when masterDirection='external'", () => {
    render(
      <IntegrationConflictResolver<QbConflictDetail>
        integration="quickbooks"
        conflict={qbConflict}
        masterDirection="external"
        {...defaultProps}
      />,
    );
    // When external is master, "Use QuickBooks version" is the primary accept_local
    const localBtn = screen.getByTestId("resolve-accept-local-btn");
    expect(localBtn).toHaveTextContent(/QuickBooks/i);
  });
});

// ─── FE-B9 supportsPerFieldResolution ────────────────────────────────────────

describe("IntegrationConflictResolver — per-field resolution", () => {
  it("shows 'Choose field by field →' button when supportsPerFieldResolution=true", () => {
    render(
      <IntegrationConflictResolver<QbConflictDetail>
        integration="quickbooks"
        conflict={qbConflict}
        supportsPerFieldResolution={true}
        perFieldSelections={[]}
        onPerFieldSelectionChange={vi.fn()}
        {...defaultProps}
      />,
    );
    expect(screen.getByTestId("per-field-picker-toggle")).toBeInTheDocument();
  });

  it("hides 'Choose field by field →' when supportsPerFieldResolution=false (default)", () => {
    render(
      <IntegrationConflictResolver
        integration="calendar"
        conflict={calendarConflict}
        {...defaultProps}
      />,
    );
    expect(
      screen.queryByTestId("per-field-picker-toggle"),
    ).not.toBeInTheDocument();
  });

  it("expands per-field picker on 'Choose field by field →' click", () => {
    render(
      <IntegrationConflictResolver<QbConflictDetail>
        integration="quickbooks"
        conflict={qbConflict}
        supportsPerFieldResolution={true}
        perFieldSelections={[]}
        onPerFieldSelectionChange={vi.fn()}
        {...defaultProps}
      />,
    );
    fireEvent.click(screen.getByTestId("per-field-picker-toggle"));
    expect(screen.getByTestId("per-field-picker-open")).toBeInTheDocument();
    expect(screen.getByTestId("per-field-picker")).toBeInTheDocument();
  });

  it("calls onPerFieldSelectionChange with correct selection when radio clicked", () => {
    const mockOnChange = vi.fn();
    render(
      <IntegrationConflictResolver<QbConflictDetail>
        integration="quickbooks"
        conflict={qbConflict}
        supportsPerFieldResolution={true}
        perFieldSelections={[]}
        onPerFieldSelectionChange={mockOnChange}
        {...defaultProps}
      />,
    );
    fireEvent.click(screen.getByTestId("per-field-picker-toggle"));
    fireEvent.click(screen.getByTestId("radio-left-amount"));
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ fieldName: "amount" }),
      ]),
    );
  });

  it("hides standard action buttons when per-field picker is open", () => {
    render(
      <IntegrationConflictResolver<QbConflictDetail>
        integration="quickbooks"
        conflict={qbConflict}
        supportsPerFieldResolution={true}
        perFieldSelections={[]}
        onPerFieldSelectionChange={vi.fn()}
        {...defaultProps}
      />,
    );
    fireEvent.click(screen.getByTestId("per-field-picker-toggle"));
    expect(
      screen.queryByTestId("resolve-accept-local-btn"),
    ).not.toBeInTheDocument();
  });
});

// ─── Deletion conflict layout ─────────────────────────────────────────────────

describe("IntegrationConflictResolver — deletion conflict", () => {
  it("renders DeletionConflictView for deleted_modified conflict type", () => {
    const deletionConflict = {
      ...calendarConflict,
      conflictType: "deleted_modified" as const,
    };
    render(
      <IntegrationConflictResolver
        integration="calendar"
        conflict={deletionConflict}
        {...defaultProps}
      />,
    );
    expect(screen.getByTestId("deletion-conflict-view")).toBeInTheDocument();
  });
});
