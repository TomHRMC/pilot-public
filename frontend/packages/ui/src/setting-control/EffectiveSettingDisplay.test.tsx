/**
 * EffectiveSettingDisplay unit tests — FE-B11
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { EffectiveSettingDisplay } from "./EffectiveSettingDisplay";

const baseProps = {
  settingKey: "background_sync_enabled",
  label: "Background sync",
  tiers: {
    system: { value: true, exists: true },
    tenant: { value: null, exists: false },
    user: { value: null, exists: false },
  },
  activeTier: "system" as const,
  userCanEdit: true,
  allowsUserOverride: true,
  displayMode: "web" as const,
  testID: "sync-enabled",
};

describe("EffectiveSettingDisplay — web mode", () => {
  it("renders three scope rows (User, Tenant, System) in web mode", () => {
    render(<EffectiveSettingDisplay {...baseProps} />);
    expect(screen.getByTestId("sync-enabled-user-row")).toBeTruthy();
    expect(screen.getByTestId("sync-enabled-tenant-row")).toBeTruthy();
    expect(screen.getByTestId("sync-enabled-system-row")).toBeTruthy();
  });

  it("active tier row (System) has distinct visual treatment", () => {
    render(<EffectiveSettingDisplay {...baseProps} activeTier="system" />);
    // System row should have bg-white shadow (active tier)
    const systemRow = screen.getByTestId("sync-enabled-system-row");
    expect(systemRow.className).toContain("shadow-sm");
  });

  it("User tier row (tenant active) has distinct treatment", () => {
    render(
      <EffectiveSettingDisplay
        {...baseProps}
        activeTier="tenant"
        tiers={{
          system: { value: true, exists: true },
          tenant: { value: false, exists: true },
          user: { value: null, exists: false },
        }}
      />,
    );
    const tenantRow = screen.getByTestId("sync-enabled-tenant-row");
    expect(tenantRow.className).toContain("shadow-sm");
  });

  it("userCanEdit=false hides edit affordance", () => {
    render(
      <EffectiveSettingDisplay
        {...baseProps}
        userCanEdit={false}
        allowsUserOverride={true}
      />,
    );
    expect(screen.queryByTestId("sync-enabled-user-toggle")).toBeNull();
  });

  it("allowsUserOverride=false shows 'Set by your tenant' annotation", () => {
    render(
      <EffectiveSettingDisplay {...baseProps} allowsUserOverride={false} />,
    );
    expect(screen.getAllByText("Set by your tenant").length).toBeGreaterThan(0);
  });

  it("calls onSaveUserOverride when user edits and saves own tier", async () => {
    const onSaveUserOverride = vi.fn().mockResolvedValue(undefined);
    render(
      <EffectiveSettingDisplay
        {...baseProps}
        onSaveUserOverride={onSaveUserOverride}
        inputType="boolean"
      />,
    );
    const toggle = screen.getByTestId("sync-enabled-user-toggle");
    fireEvent.click(toggle);
    await waitFor(() => expect(onSaveUserOverride).toHaveBeenCalled());
  });

  it("calls onRevertUserOverride on 'Match tenant' click when user override exists", () => {
    const onRevertUserOverride = vi.fn().mockResolvedValue(undefined);
    render(
      <EffectiveSettingDisplay
        {...baseProps}
        activeTier="user"
        tiers={{
          system: { value: true, exists: true },
          tenant: { value: false, exists: true },
          user: { value: true, exists: true },
        }}
        onRevertUserOverride={onRevertUserOverride}
      />,
    );
    const matchTenantBtn = screen.getByTestId("sync-enabled-user-revert");
    fireEvent.click(matchTenantBtn);
    expect(onRevertUserOverride).toHaveBeenCalled();
  });
});

describe("EffectiveSettingDisplay — mobile mode", () => {
  it("displayMode=mobile shows user tier + tenant tier", () => {
    render(
      <EffectiveSettingDisplay
        {...baseProps}
        displayMode="mobile"
        testID="sync-mobile"
      />,
    );
    expect(screen.getByTestId("sync-mobile-mobile-user-row")).toBeTruthy();
  });

  it("displayMode=mobile hides system tier when same as tenant", () => {
    render(
      <EffectiveSettingDisplay
        {...baseProps}
        displayMode="mobile"
        activeTier="tenant"
        tiers={{
          system: { value: true, exists: true },
          tenant: { value: true, exists: true },
          user: { value: null, exists: false },
        }}
        testID="sync-mobile"
      />,
    );
    // System row should be absent when tenant == system
    expect(screen.queryByText("System")).toBeNull();
  });
});
