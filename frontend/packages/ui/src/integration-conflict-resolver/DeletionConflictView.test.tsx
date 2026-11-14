/**
 * DeletionConflictView unit tests
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DeletionConflictView } from "./DeletionConflictView";

const baseProps = {
  jobTitle: "Panel Upgrade - Smith Residence",
  onResolve: vi.fn(),
  isResolving: false,
  onResolveLater: vi.fn(),
};

describe("<DeletionConflictView>", () => {
  describe("deleted_modified conflict type", () => {
    it("renders 'Restore the Job from Calendar' as primary action", () => {
      render(
        <DeletionConflictView {...baseProps} conflictType="deleted_modified" />,
      );
      expect(screen.getByTestId("deletion-primary-btn")).toHaveTextContent(
        "Restore the Job from Calendar",
      );
    });

    it("renders 'Delete from Calendar Too' as destructive action", () => {
      render(
        <DeletionConflictView {...baseProps} conflictType="deleted_modified" />,
      );
      expect(screen.getByTestId("deletion-destructive-btn")).toHaveTextContent(
        "Delete from Calendar Too",
      );
    });

    it("calls onResolve with 'restore_from_calendar' when primary button clicked", () => {
      const onResolve = vi.fn();
      render(
        <DeletionConflictView
          {...baseProps}
          conflictType="deleted_modified"
          onResolve={onResolve}
        />,
      );
      fireEvent.click(screen.getByTestId("deletion-primary-btn"));
      expect(onResolve).toHaveBeenCalledWith("restore_from_calendar");
    });

    it("calls onResolve with 'delete_calendar_too' when destructive button clicked", () => {
      const onResolve = vi.fn();
      render(
        <DeletionConflictView
          {...baseProps}
          conflictType="deleted_modified"
          onResolve={onResolve}
        />,
      );
      fireEvent.click(screen.getByTestId("deletion-destructive-btn"));
      expect(onResolve).toHaveBeenCalledWith("delete_calendar_too");
    });
  });

  describe("modified_deleted conflict type", () => {
    it("renders 'Recreate the Calendar Event' as primary action", () => {
      render(
        <DeletionConflictView {...baseProps} conflictType="modified_deleted" />,
      );
      expect(screen.getByTestId("deletion-primary-btn")).toHaveTextContent(
        "Recreate the Calendar Event",
      );
    });

    it("renders 'Delete the Pilot Job' as destructive action", () => {
      render(
        <DeletionConflictView {...baseProps} conflictType="modified_deleted" />,
      );
      expect(screen.getByTestId("deletion-destructive-btn")).toHaveTextContent(
        "Delete the Pilot Job",
      );
    });

    it("calls onResolve with 'recreate_calendar_event' when primary button clicked", () => {
      const onResolve = vi.fn();
      render(
        <DeletionConflictView
          {...baseProps}
          conflictType="modified_deleted"
          onResolve={onResolve}
        />,
      );
      fireEvent.click(screen.getByTestId("deletion-primary-btn"));
      expect(onResolve).toHaveBeenCalledWith("recreate_calendar_event");
    });

    it("calls onResolve with 'delete_pilot_job' when destructive button clicked", () => {
      const onResolve = vi.fn();
      render(
        <DeletionConflictView
          {...baseProps}
          conflictType="modified_deleted"
          onResolve={onResolve}
        />,
      );
      fireEvent.click(screen.getByTestId("deletion-destructive-btn"));
      expect(onResolve).toHaveBeenCalledWith("delete_pilot_job");
    });
  });

  it("disables all buttons when isResolving=true", () => {
    render(
      <DeletionConflictView
        {...baseProps}
        conflictType="deleted_modified"
        isResolving={true}
      />,
    );
    expect(screen.getByTestId("deletion-primary-btn")).toBeDisabled();
    expect(screen.getByTestId("deletion-destructive-btn")).toBeDisabled();
    expect(screen.getByTestId("deletion-resolve-later-btn")).toBeDisabled();
  });

  it("shows 'Resolving…' spinner text when isResolving=true", () => {
    render(
      <DeletionConflictView
        {...baseProps}
        conflictType="deleted_modified"
        isResolving={true}
      />,
    );
    expect(screen.getByTestId("deletion-primary-btn")).toHaveTextContent(
      "Resolving…",
    );
  });

  it("calls onResolveLater when 'Resolve later' button clicked", () => {
    const onResolveLater = vi.fn();
    render(
      <DeletionConflictView
        {...baseProps}
        conflictType="deleted_modified"
        onResolveLater={onResolveLater}
      />,
    );
    fireEvent.click(screen.getByTestId("deletion-resolve-later-btn"));
    expect(onResolveLater).toHaveBeenCalledTimes(1);
  });

  it("renders job title in context banner", () => {
    render(
      <DeletionConflictView {...baseProps} conflictType="deleted_modified" />,
    );
    expect(
      screen.getByText(/Panel Upgrade - Smith Residence/),
    ).toBeInTheDocument();
  });

  it("renders context banner with amber tokens", () => {
    const { container } = render(
      <DeletionConflictView {...baseProps} conflictType="deleted_modified" />,
    );
    const banner = container.querySelector('[role="alert"]');
    expect(banner?.className).toContain("bg-alert-50");
    expect(banner?.className).toContain("border-alert-200");
  });
});
