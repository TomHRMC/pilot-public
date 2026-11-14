/**
 * Cross-field validation integration test — FE-B11
 */

import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import {
  settingsHandlers,
  resetSettingsScenario,
} from "../../src/features/settings/mocks/settingsHandlers";
import { CalendarAutoExpirySettings } from "../../src/features/calendar-conflict/components/CalendarAutoExpirySettings";
import type { CatalogEntry } from "@pilot/ui";
import { createSettingsWrapper } from "../test-utils/settingsWrapper";

const server = setupServer(...settingsHandlers);

beforeEach(() => {
  server.listen({ onUnhandledRequest: "bypass" });
  resetSettingsScenario();
});
afterEach(() => {
  server.resetHandlers();
  server.close();
});

const autoExpireEntry: CatalogEntry = {
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

describe("Cross-field validation — CalendarAutoExpirySettings", () => {
  it("renders both fields", () => {
    const { wrapper } = createSettingsWrapper();
    render(
      <CalendarAutoExpirySettings
        onSavePreWarning={async () => {}}
        onSaveAutoExpiry={async () => {}}
      />,
      { wrapper },
    );
    expect(screen.getByTestId("auto-expire-days-input")).toBeTruthy();
    expect(screen.getByTestId("pre-warning-days-input")).toBeTruthy();
  });

  it("shows cross-field error when pre_warning >= auto_expire", async () => {
    const { wrapper } = createSettingsWrapper();
    const onSavePreWarning = async (val: unknown) => {
      if (Number(val) >= 30) {
        throw new Error(
          "Pre-warning period must be less than auto-expiry days (30).",
        );
      }
    };

    render(
      <CalendarAutoExpirySettings
        autoExpiryCatalogEntry={autoExpireEntry}
        onSaveAutoExpiry={async () => {}}
        onSavePreWarning={onSavePreWarning}
      />,
      { wrapper },
    );

    const preWarningInput = screen.getByTestId("pre-warning-days-input-input");
    fireEvent.change(preWarningInput, { target: { value: "30" } });
    fireEvent.blur(preWarningInput);

    await waitFor(
      () =>
        expect(screen.getByTestId("pre-warning-days-input-error")).toBeTruthy(),
      { timeout: 3000 },
    );
  });
});
