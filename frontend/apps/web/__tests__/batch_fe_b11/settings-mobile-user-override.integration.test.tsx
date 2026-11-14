/**
 * Mobile user override integration test — FE-B11
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { EffectiveSettingDisplay } from "@pilot/ui";

describe("EffectiveSettingDisplay — mobile per-user override", () => {
  it("renders user tier with editable toggle", () => {
    render(
      <EffectiveSettingDisplay
        settingKey="background_sync_enabled"
        label="Background sync"
        tiers={{
          system: { value: true, exists: true },
          tenant: { value: true, exists: true },
          user: { value: false, exists: true },
        }}
        activeTier="user"
        userCanEdit
        allowsUserOverride
        onSaveUserOverride={vi.fn().mockResolvedValue(undefined)}
        onRevertUserOverride={vi.fn().mockResolvedValue(undefined)}
        inputType="boolean"
        displayMode="mobile"
        testID="sync-mobile"
      />,
    );
    expect(screen.getByTestId("sync-mobile-mobile-user-row")).toBeTruthy();
    expect(screen.getByTestId("sync-mobile-mobile-toggle")).toBeTruthy();
  });

  it("shows 'Match tenant default' link when user override exists", () => {
    render(
      <EffectiveSettingDisplay
        settingKey="background_sync_enabled"
        label="Background sync"
        tiers={{
          system: { value: true, exists: true },
          tenant: { value: true, exists: true },
          user: { value: false, exists: true },
        }}
        activeTier="user"
        userCanEdit
        allowsUserOverride
        onSaveUserOverride={vi.fn().mockResolvedValue(undefined)}
        onRevertUserOverride={vi.fn().mockResolvedValue(undefined)}
        inputType="boolean"
        displayMode="mobile"
        testID="sync-mobile"
      />,
    );
    expect(screen.getByTestId("sync-mobile-mobile-match-tenant")).toBeTruthy();
  });

  it("calls onRevertUserOverride when 'Match tenant default' pressed", async () => {
    const onRevertUserOverride = vi.fn().mockResolvedValue(undefined);
    render(
      <EffectiveSettingDisplay
        settingKey="background_sync_enabled"
        label="Background sync"
        tiers={{
          system: { value: true, exists: true },
          tenant: { value: true, exists: true },
          user: { value: false, exists: true },
        }}
        activeTier="user"
        userCanEdit
        allowsUserOverride
        onSaveUserOverride={vi.fn().mockResolvedValue(undefined)}
        onRevertUserOverride={onRevertUserOverride}
        inputType="boolean"
        displayMode="mobile"
        testID="sync-mobile"
      />,
    );
    fireEvent.click(screen.getByTestId("sync-mobile-mobile-match-tenant"));
    await waitFor(() => expect(onRevertUserOverride).toHaveBeenCalled());
  });
});
