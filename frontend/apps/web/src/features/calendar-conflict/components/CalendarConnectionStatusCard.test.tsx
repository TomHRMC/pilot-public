/**
 * CalendarConnectionStatusCard unit tests
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CalendarConnectionStatusCard } from "./CalendarConnectionStatusCard";
import type { CalendarConnectionStatus } from "@pilot/ui";

const connectedStatus: CalendarConnectionStatus = {
  isConnected: true,
  providerCode: "google_calendar",
  syncStatus: "idle",
  connectionStatus: "connected",
  connectedAt: "2026-05-01T08:00:00Z",
  tokenExpiresAt: "2026-08-01T08:00:00Z",
  lastSyncAt: "2026-05-25T17:00:00Z",
  lastSuccessfulSyncAt: "2026-05-25T17:00:00Z",
  pendingConflictsCount: 0,
  requiresReconnect: false,
};

const conflictsStatus: CalendarConnectionStatus = {
  ...connectedStatus,
  pendingConflictsCount: 3,
};

const errorStatus: CalendarConnectionStatus = {
  ...connectedStatus,
  connectionStatus: "error",
  requiresReconnect: true,
  pendingConflictsCount: 5,
};

const disconnectedStatus: CalendarConnectionStatus = {
  isConnected: false,
  providerCode: null,
  syncStatus: null,
  connectionStatus: "disconnected",
  connectedAt: null,
  tokenExpiresAt: null,
  lastSyncAt: null,
  lastSuccessfulSyncAt: null,
  pendingConflictsCount: 0,
  requiresReconnect: false,
};

describe("<CalendarConnectionStatusCard>", () => {
  it("renders loading state when isLoading=true", () => {
    render(
      <CalendarConnectionStatusCard status={undefined} isLoading={true} />,
    );
    expect(screen.getByText("Loading calendar status…")).toBeInTheDocument();
  });

  it("renders disconnected state when not connected", () => {
    render(
      <CalendarConnectionStatusCard
        status={disconnectedStatus}
        isLoading={false}
      />,
    );
    expect(screen.getByText("No calendar connected")).toBeInTheDocument();
    expect(
      screen.getByTestId("calendar-status-dot-disconnected"),
    ).toBeInTheDocument();
  });

  it("renders connect button for disconnected state when onConnect provided", () => {
    const onConnect = vi.fn();
    render(
      <CalendarConnectionStatusCard
        status={disconnectedStatus}
        isLoading={false}
        onConnect={onConnect}
      />,
    );
    const btn = screen.getByTestId("calendar-connect-btn");
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onConnect).toHaveBeenCalledTimes(1);
  });

  it("renders green dot for connected status with no conflicts", () => {
    render(
      <CalendarConnectionStatusCard
        status={connectedStatus}
        isLoading={false}
      />,
    );
    expect(
      screen.getByTestId("calendar-status-dot-connected"),
    ).toBeInTheDocument();
    const dot = screen.getByTestId("calendar-status-dot-connected");
    expect(dot.className).toContain("bg-margin-400");
  });

  it("renders amber dot for pending conflicts", () => {
    render(
      <CalendarConnectionStatusCard
        status={conflictsStatus}
        isLoading={false}
      />,
    );
    expect(
      screen.getByTestId("calendar-status-dot-conflicts"),
    ).toBeInTheDocument();
    expect(screen.getByText(/3 conflicts pending/)).toBeInTheDocument();
    const dot = screen.getByTestId("calendar-status-dot-conflicts");
    expect(dot.className).toContain("bg-alert-400");
  });

  it("renders red dot for error/requires_reconnect", () => {
    render(
      <CalendarConnectionStatusCard
        status={errorStatus}
        isLoading={false}
        onReconnect={vi.fn()}
      />,
    );
    expect(screen.getByTestId("calendar-status-dot-error")).toBeInTheDocument();
    const dot = screen.getByTestId("calendar-status-dot-error");
    expect(dot.className).toContain("bg-fault-600");
  });

  it("renders reconnect button when error and onReconnect provided", () => {
    const onReconnect = vi.fn();
    render(
      <CalendarConnectionStatusCard
        status={errorStatus}
        isLoading={false}
        onReconnect={onReconnect}
      />,
    );
    const btn = screen.getByTestId("calendar-reconnect-btn");
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onReconnect).toHaveBeenCalledTimes(1);
  });

  it("renders error NotificationBanner for error state", () => {
    render(
      <CalendarConnectionStatusCard
        status={errorStatus}
        isLoading={false}
        onReconnect={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/Sync error blocking automatic conflict push/),
    ).toBeInTheDocument();
  });

  it("renders 'Reconnect needed' label for error state", () => {
    render(
      <CalendarConnectionStatusCard status={errorStatus} isLoading={false} />,
    );
    expect(screen.getByText(/Reconnect needed/)).toBeInTheDocument();
  });

  it("uses custom testID", () => {
    render(
      <CalendarConnectionStatusCard
        status={connectedStatus}
        isLoading={false}
        testID="my-status-card"
      />,
    );
    expect(screen.getByTestId("my-status-card")).toBeInTheDocument();
  });
});
