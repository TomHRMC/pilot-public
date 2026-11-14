/**
 * Mobile read-only integration test — FE-B11
 */

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SettingControl } from "@pilot/ui";

describe("SettingControl readOnly — mobile provenance annotation", () => {
  it("renders value without any input", () => {
    render(
      <SettingControl
        settingKey="background_sync_battery_floor_pct"
        label="Minimum battery for sync"
        value={20}
        defaultValue={20}
        scope="system"
        saveMode="blur"
        onSave={async () => {}}
        readOnly
        provenanceAnnotation="system"
        testID="battery-floor-readonly"
      />,
    );
    expect(
      screen.queryByTestId("setting-input-background_sync_battery_floor_pct"),
    ).toBeNull();
    expect(screen.getByText("20")).toBeTruthy();
  });

  it("shows 'Default value' annotation when scope=system", () => {
    render(
      <SettingControl
        settingKey="background_sync_wifi_only"
        label="Sync on Wi-Fi only"
        value={true}
        defaultValue={true}
        scope="system"
        saveMode="blur"
        onSave={async () => {}}
        readOnly
        provenanceAnnotation="system"
        testID="wifi-only-readonly"
      />,
    );
    expect(screen.getByText("Default value")).toBeTruthy();
  });

  it("shows 'Set by your tenant' annotation when scope=tenant", () => {
    render(
      <SettingControl
        settingKey="background_sync_battery_floor_pct"
        label="Minimum battery for sync"
        value={30}
        defaultValue={20}
        scope="tenant"
        saveMode="blur"
        onSave={async () => {}}
        readOnly
        provenanceAnnotation="tenant"
        testID="battery-floor-tenant"
      />,
    );
    expect(screen.getByText("Set by your tenant")).toBeTruthy();
  });

  it("no revert affordance in readOnly mode", () => {
    render(
      <SettingControl
        settingKey="wifi_only"
        label="WiFi only"
        value={true}
        defaultValue={true}
        scope="tenant"
        saveMode="blur"
        onSave={async () => {}}
        readOnly
        onRevert={async () => {}}
        testID="wifi-readonly"
      />,
    );
    expect(screen.queryByTestId("setting-revert-link-wifi_only")).toBeNull();
  });
});
