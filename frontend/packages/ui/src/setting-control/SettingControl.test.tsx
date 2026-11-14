/**
 * SettingControl unit tests — FE-B11
 *
 * Location: packages/ui/src/setting-control/SettingControl.test.tsx
 *
 * Target: 22+ test cases covering State 1/2 transitions, save phases,
 * error handling, revert flow, readOnly mode, and input types.
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { SettingControl } from "./SettingControl";

const baseProps = {
  settingKey: "test_setting",
  label: "Test Setting",
  value: 30 as unknown,
  defaultValue: 30 as unknown,
  scope: "system" as const,
  saveMode: "blur" as const,
  onSave: vi.fn().mockResolvedValue(undefined),
};

describe("SettingControl — State 1 (scope=system)", () => {
  it("renders label correctly", () => {
    render(<SettingControl {...baseProps} />);
    expect(screen.getByText("Test Setting")).toBeTruthy();
  });

  it("renders State 1 muted annotation 'Default · 30' when scope=system", () => {
    render(<SettingControl {...baseProps} />);
    expect(screen.getByTestId("setting-default-test_setting")).toBeTruthy();
    expect(screen.getByText(/Default · 30/)).toBeTruthy();
  });

  it("does NOT render 'Revert to default' link when scope=system", () => {
    render(<SettingControl {...baseProps} />);
    expect(screen.queryByTestId("setting-revert-link-test_setting")).toBeNull();
  });

  it("renders description when provided", () => {
    render(
      <SettingControl {...baseProps} description="A helpful description" />,
    );
    expect(screen.getByText("A helpful description")).toBeTruthy();
  });
});

describe("SettingControl — State 2 (scope=tenant)", () => {
  const state2Props = {
    ...baseProps,
    value: 45 as unknown,
    scope: "tenant" as const,
  };

  it("renders State 2: 'tenant override' pill visible", () => {
    render(<SettingControl {...state2Props} />);
    expect(screen.getByText("tenant override")).toBeTruthy();
  });

  it("renders State 2: 'Revert to default' link IS visible", () => {
    render(
      <SettingControl
        {...state2Props}
        onRevert={vi.fn().mockResolvedValue(undefined)}
      />,
    );
    expect(screen.getByTestId("setting-revert-link-test_setting")).toBeTruthy();
  });

  it("State 2: muted annotation is NOT visible", () => {
    render(<SettingControl {...state2Props} />);
    expect(screen.queryByTestId("setting-default-test_setting")).toBeNull();
  });
});

describe("SettingControl — State 1 → State 2 transition", () => {
  it("calls onSave on field blur (saveMode=blur)", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <SettingControl {...baseProps} onSave={onSave} inputType="integer" />,
    );

    const input = screen.getByTestId("setting-input-test_setting");
    fireEvent.change(input, { target: { value: "45" } });
    fireEvent.blur(input);

    await waitFor(() => expect(onSave).toHaveBeenCalledWith(45));
  });

  it("shows pending spinner during save-pending phase", async () => {
    let resolveSave: () => void;
    const onSave = vi.fn().mockReturnValue(
      new Promise<void>((r) => {
        resolveSave = r;
      }),
    );
    render(
      <SettingControl {...baseProps} onSave={onSave} inputType="integer" />,
    );

    const input = screen.getByTestId("setting-input-test_setting");
    fireEvent.change(input, { target: { value: "45" } });
    fireEvent.blur(input);

    await waitFor(() =>
      expect(screen.getByTestId("setting-pending-test_setting")).toBeTruthy(),
    );
    act(() => resolveSave!());
  });

  it("shows 'Saved' text after successful save", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <SettingControl {...baseProps} onSave={onSave} inputType="integer" />,
    );

    const input = screen.getByTestId("setting-input-test_setting");
    fireEvent.change(input, { target: { value: "45" } });
    fireEvent.blur(input);

    await waitFor(() =>
      expect(screen.getByTestId("setting-saved-test_setting")).toBeTruthy(),
    );
  });
});

describe("SettingControl — Error / rollback", () => {
  it("reverts to pre-edit value on onSave rejection", async () => {
    const onSave = vi.fn().mockRejectedValue(new Error("Server error"));
    render(
      <SettingControl
        {...baseProps}
        value={30 as unknown}
        onSave={onSave}
        inputType="integer"
      />,
    );

    const input = screen.getByTestId(
      "setting-input-test_setting",
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "99" } });
    fireEvent.blur(input);

    await waitFor(() => expect(input.value).toBe("30"));
  });

  it("shows inline error text on save failure", async () => {
    const onSave = vi.fn().mockRejectedValue(new Error("Server error"));
    render(
      <SettingControl {...baseProps} onSave={onSave} inputType="integer" />,
    );

    const input = screen.getByTestId("setting-input-test_setting");
    fireEvent.change(input, { target: { value: "99" } });
    fireEvent.blur(input);

    await waitFor(() =>
      expect(screen.getByTestId("setting-error-test_setting")).toBeTruthy(),
    );
  });
});

describe("SettingControl — Revert to default", () => {
  const state2WithRevert = {
    ...baseProps,
    value: 45 as unknown,
    scope: "tenant" as const,
    onRevert: vi.fn().mockResolvedValue(undefined),
  };

  it("enters revert-pending phase when 'Revert to default' clicked", () => {
    render(<SettingControl {...state2WithRevert} />);
    fireEvent.click(screen.getByTestId("setting-revert-link-test_setting"));
    expect(
      screen.getByTestId("setting-revert-dialog-test_setting"),
    ).toBeTruthy();
  });

  it("shows RevertToDefaultDialog with current + default values", () => {
    render(<SettingControl {...state2WithRevert} unit="days" />);
    fireEvent.click(screen.getByTestId("setting-revert-link-test_setting"));
    // Dialog shows current value 45 and default value 30
    expect(screen.getByText(/45/)).toBeTruthy();
    expect(screen.getByText(/30/)).toBeTruthy();
  });

  it("calls onRevert on confirm and transitions to State 1", async () => {
    const onRevert = vi.fn().mockResolvedValue(undefined);
    render(
      <SettingControl
        {...baseProps}
        value={45 as unknown}
        scope="tenant"
        onRevert={onRevert}
      />,
    );
    fireEvent.click(screen.getByTestId("setting-revert-link-test_setting"));
    fireEvent.click(
      screen.getByTestId("setting-revert-dialog-test_setting-confirm"),
    );
    await waitFor(() => expect(onRevert).toHaveBeenCalled());
  });

  it("returns to State 2 on cancel revert", () => {
    render(<SettingControl {...state2WithRevert} />);
    fireEvent.click(screen.getByTestId("setting-revert-link-test_setting"));
    fireEvent.click(
      screen.getByTestId("setting-revert-dialog-test_setting-cancel"),
    );
    expect(
      screen.queryByTestId("setting-revert-dialog-test_setting"),
    ).toBeNull();
    expect(screen.getByText("tenant override")).toBeTruthy();
  });
});

describe("SettingControl — readOnly mode", () => {
  it("renders value without edit affordance when readOnly=true", () => {
    render(
      <SettingControl {...baseProps} readOnly provenanceAnnotation="tenant" />,
    );
    expect(screen.queryByTestId("setting-input-test_setting")).toBeNull();
    expect(screen.queryByTestId("setting-toggle-test_setting")).toBeNull();
  });

  it("shows provenance annotation 'Set by your tenant' when scope=tenant", () => {
    render(
      <SettingControl
        {...baseProps}
        scope="tenant"
        readOnly
        provenanceAnnotation="tenant"
      />,
    );
    expect(screen.getByTestId("setting-provenance-test_setting")).toBeTruthy();
    expect(screen.getByText("Set by your tenant")).toBeTruthy();
  });

  it("shows provenance annotation 'Default value' when scope=system", () => {
    render(
      <SettingControl {...baseProps} readOnly provenanceAnnotation="system" />,
    );
    expect(screen.getByText("Default value")).toBeTruthy();
  });

  it("no revert affordance when readOnly=true", () => {
    render(
      <SettingControl
        {...baseProps}
        scope="tenant"
        readOnly
        onRevert={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("setting-revert-link-test_setting")).toBeNull();
  });
});

describe("SettingControl — effectiveRangeLabel", () => {
  it("renders effectiveRangeLabel helper text", () => {
    render(
      <SettingControl
        {...baseProps}
        effectiveRangeLabel="Effective: 30 days · Pre-warning at: 7 days"
      />,
    );
    expect(
      screen.getByText("Effective: 30 days · Pre-warning at: 7 days"),
    ).toBeTruthy();
  });
});

describe("SettingControl — inputType=boolean (toggle)", () => {
  it("renders toggle for boolean inputType", () => {
    render(
      <SettingControl
        {...baseProps}
        value={false as unknown}
        defaultValue={false as unknown}
        inputType="boolean"
      />,
    );
    expect(screen.getByTestId("setting-toggle-test_setting")).toBeTruthy();
  });

  it("toggle change calls onSave immediately (saveMode=blur)", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <SettingControl
        {...baseProps}
        value={false as unknown}
        defaultValue={false as unknown}
        inputType="boolean"
        onSave={onSave}
      />,
    );
    fireEvent.click(screen.getByTestId("setting-toggle-test_setting"));
    await waitFor(() => expect(onSave).toHaveBeenCalledWith(true));
  });
});

describe("SettingControl — inputType=select", () => {
  it("renders dropdown with options", () => {
    render(
      <SettingControl
        {...baseProps}
        value={"standard" as unknown}
        defaultValue={"standard" as unknown}
        inputType="select"
        selectOptions={[
          { value: "standard", label: "Standard" },
          { value: "overtime", label: "Overtime" },
        ]}
      />,
    );
    expect(screen.getByTestId("setting-select-test_setting")).toBeTruthy();
    expect(screen.getByText("Standard")).toBeTruthy();
    expect(screen.getByText("Overtime")).toBeTruthy();
  });
});

describe("SettingControl — validation", () => {
  it("enforces min validation and blocks save when out of range", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <SettingControl
        {...baseProps}
        value={10 as unknown}
        onSave={onSave}
        validationRules={{ min: 5, max: 50 }}
        inputType="integer"
      />,
    );

    const input = screen.getByTestId("setting-input-test_setting");
    fireEvent.change(input, { target: { value: "2" } });
    fireEvent.blur(input);

    await waitFor(() =>
      expect(screen.getByTestId("setting-error-test_setting")).toBeTruthy(),
    );
    expect(onSave).not.toHaveBeenCalled();
  });

  it("enforces max validation", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <SettingControl
        {...baseProps}
        value={10 as unknown}
        onSave={onSave}
        validationRules={{ min: 1, max: 30 }}
        inputType="integer"
      />,
    );

    const input = screen.getByTestId("setting-input-test_setting");
    fireEvent.change(input, { target: { value: "99" } });
    fireEvent.blur(input);

    await waitFor(() =>
      expect(screen.getByTestId("setting-error-test_setting")).toBeTruthy(),
    );
    expect(onSave).not.toHaveBeenCalled();
  });
});
