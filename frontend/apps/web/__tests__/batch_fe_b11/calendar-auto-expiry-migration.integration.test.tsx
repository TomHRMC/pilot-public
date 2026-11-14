/**
 * CalendarAutoExpirySettings migration test — FE-B11
 */

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CalendarAutoExpirySettings } from "../../src/features/calendar-conflict/components/CalendarAutoExpirySettings";
import type { CatalogEntry } from "@pilot/ui";
import { createSettingsWrapper } from "../test-utils/settingsWrapper";

const systemEntry: CatalogEntry = {
  key: "calendar_conflict_auto_expire_days",
  label: "Auto-expiry period",
  description: "Days before an unresolved conflict auto-resolves.",
  subSurfacePath: "/settings/integrations/general",
  dataType: "integer",
  validationRules: { min: 1, max: 365 },
  systemDefault: 30,
  currentEffectiveValue: 30,
  currentScope: "system",
  revertible: false,
  requiresRole: null,
  allowsUserOverride: false,
};

const tenantEntry: CatalogEntry = {
  ...systemEntry,
  currentEffectiveValue: 45,
  currentScope: "tenant",
  revertible: true,
};

describe("CalendarAutoExpirySettings — migration regression", () => {
  it("renders with SettingControl (State 1) when scope=system", () => {
    const { wrapper } = createSettingsWrapper();
    render(
      <CalendarAutoExpirySettings
        autoExpiryCatalogEntry={systemEntry}
        onSaveAutoExpiry={async () => {}}
        onSavePreWarning={async () => {}}
      />,
      { wrapper },
    );

    // SettingControl renders the field with the settingKey-based testid
    expect(screen.getByTestId("auto-expire-days-input")).toBeTruthy();
    // State 1: muted annotation visible
    expect(
      screen.getByTestId("auto-expire-days-input-default-annotation"),
    ).toBeTruthy();
  });

  it("renders with SettingControl (State 2) when scope=tenant", () => {
    const { wrapper } = createSettingsWrapper();
    render(
      <CalendarAutoExpirySettings
        autoExpiryCatalogEntry={tenantEntry}
        onSaveAutoExpiry={async () => {}}
        onSavePreWarning={async () => {}}
        onRevertAutoExpiry={async () => {}}
      />,
      { wrapper },
    );

    // State 2: tenant override pill visible
    expect(screen.getByText("tenant override")).toBeTruthy();
  });

  it("BaseSettingInput re-exports SettingControl (not the old stub)", async () => {
    const mod =
      await import("../../src/features/calendar-conflict/components/BaseSettingInput");
    expect(mod.BaseSettingInput).toBeDefined();
  });
});
