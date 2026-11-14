/**
 * SaveOnGroupCompleteIndicator unit tests — FE-B11
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { SaveOnGroupCompleteIndicator } from "./SaveOnGroupCompleteIndicator";

describe("SaveOnGroupCompleteIndicator — incomplete group", () => {
  it("shows incomplete-group state when groupIsComplete=false", () => {
    render(
      <SaveOnGroupCompleteIndicator
        groupIsComplete={false}
        incompleteFields={["qb_auto_expire_invoice_direction"]}
        savedAt={null}
        savePending={false}
        error={null}
        testID="group-indicator"
      />,
    );
    expect(screen.getByTestId("group-indicator-incomplete")).toBeTruthy();
  });

  it("shows incompletePrompt text", () => {
    render(
      <SaveOnGroupCompleteIndicator
        groupIsComplete={false}
        incompleteFields={["direction"]}
        savedAt={null}
        savePending={false}
        error={null}
        incompletePrompt="Pick a direction to complete this setting."
        testID="group-indicator"
      />,
    );
    expect(
      screen.getByText("Pick a direction to complete this setting."),
    ).toBeTruthy();
  });

  it("does not render when group is complete and no status", () => {
    const { container } = render(
      <SaveOnGroupCompleteIndicator
        groupIsComplete
        incompleteFields={[]}
        savedAt={null}
        savePending={false}
        error={null}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});

describe("SaveOnGroupCompleteIndicator — pending", () => {
  it("shows spinner when savePending=true", () => {
    render(
      <SaveOnGroupCompleteIndicator
        groupIsComplete
        incompleteFields={[]}
        savedAt={null}
        savePending
        error={null}
        testID="group-indicator"
      />,
    );
    expect(screen.getByTestId("group-indicator-pending")).toBeTruthy();
  });
});

describe("SaveOnGroupCompleteIndicator — saved", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("shows Saved tick when savedAt is recent (< 2s)", () => {
    render(
      <SaveOnGroupCompleteIndicator
        groupIsComplete
        incompleteFields={[]}
        savedAt={Date.now()}
        savePending={false}
        error={null}
        testID="group-indicator"
      />,
    );
    expect(screen.getByTestId("group-indicator-saved")).toBeTruthy();
  });

  it("hides Saved tick after 2s", async () => {
    const { rerender } = render(
      <SaveOnGroupCompleteIndicator
        groupIsComplete
        incompleteFields={[]}
        savedAt={Date.now()}
        savePending={false}
        error={null}
        testID="group-indicator"
      />,
    );
    act(() => vi.advanceTimersByTime(2100));
    rerender(
      <SaveOnGroupCompleteIndicator
        groupIsComplete
        incompleteFields={[]}
        savedAt={Date.now() - 2200}
        savePending={false}
        error={null}
        testID="group-indicator"
      />,
    );
    expect(screen.queryByTestId("group-indicator-saved")).toBeNull();
  });
});

describe("SaveOnGroupCompleteIndicator — error", () => {
  it("shows error text when error non-null", () => {
    render(
      <SaveOnGroupCompleteIndicator
        groupIsComplete
        incompleteFields={[]}
        savedAt={null}
        savePending={false}
        error="Couldn't save — try again."
        testID="group-indicator"
      />,
    );
    expect(screen.getByTestId("group-indicator-error")).toBeTruthy();
    expect(screen.getByText("Couldn't save — try again.")).toBeTruthy();
  });
});
