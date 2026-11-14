/**
 * MessagingSetupChecklistItem unit tests — C-B5
 *
 * Location: apps/web/src/features/onboarding/components/__tests__/MessagingSetupChecklistItem.test.tsx
 *
 * Verifies:
 *  - Incomplete state shows "Set up" link
 *  - Complete state shows strikethrough + no link
 */

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessagingSetupChecklistItem } from "../MessagingSetupChecklistItem";

describe("MessagingSetupChecklistItem", () => {
  it("incomplete state shows Set up link", () => {
    render(
      <MessagingSetupChecklistItem isComplete={false} onNavigate={() => {}} />,
    );
    const link = screen.getByTestId("checklist-action-messagingSetup");
    expect(link).toHaveTextContent("Set up");
    // Label is not strikethrough
    const label = screen.getByTestId("checklist-label-messagingSetup");
    expect(label).not.toHaveClass("line-through");
  });

  it("complete state shows strikethrough + no link", () => {
    render(
      <MessagingSetupChecklistItem isComplete={true} onNavigate={() => {}} />,
    );
    const label = screen.getByTestId("checklist-label-messagingSetup");
    expect(label).toHaveClass("line-through");
    // No action link rendered
    expect(
      screen.queryByTestId("checklist-action-messagingSetup"),
    ).not.toBeInTheDocument();
  });
});
