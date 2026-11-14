/**
 * DisabledAccountExportScreen Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/disabled-account.unit.test.tsx
 *
 * Tests: renders on account-disabled; export button triggers share sheet;
 *        JSON structure is correct.
 *
 * Per batch-fe-b7-design.md Section I.1.
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react-native";
import { DisabledAccountExportScreen } from "../../features/offline-sync/components/DisabledAccountExportScreen";

// Mock expo-file-system and expo-file-system/legacy.
// DisabledAccountExportScreen imports from expo-file-system/legacy after the
// v17→v19 upgrade moved legacy APIs to that sub-path.
// expo-file-system/legacy is redirected by moduleNameMapper to
// __mocks__/expo-file-system-legacy.js which exports jest.fn() stubs.
// We also mock the root package for completeness.
jest.mock("expo-file-system", () => ({
  writeAsStringAsync: jest.fn().mockResolvedValue(undefined),
  cacheDirectory: "/tmp/",
  EncodingType: { UTF8: "utf8", Base64: "base64" },
}));
// expo-file-system/legacy is handled by moduleNameMapper →
// __mocks__/expo-file-system-legacy.js (no jest.mock() needed here)

// Mock expo-sharing
jest.mock("expo-sharing", () => ({
  isAvailableAsync: jest.fn().mockResolvedValue(true),
  shareAsync: jest.fn().mockResolvedValue(undefined),
}));

// Mock WatermelonDB database
jest.mock("../../database", () => ({
  database: {
    get: jest.fn().mockReturnValue({
      query: jest.fn().mockReturnValue({
        fetch: jest.fn().mockResolvedValue([
          {
            id: "record-001",
            _raw: {
              job_id: "job-001",
              user_id: "user-001",
              started_at: Date.now(),
              local_sync_status: "pending",
              idempotency_key: "uuid-001",
            },
          },
        ]),
      }),
    }),
  },
}));

describe("DisabledAccountExportScreen", () => {
  const props = {
    userId: "user-001",
    tenantId: "tenant-001",
  };

  it("renders account disabled message", () => {
    render(<DisabledAccountExportScreen {...props} testID="export-screen" />);
    expect(screen.getByText("Account Disabled")).toBeTruthy();
  });

  it("renders export button", () => {
    render(<DisabledAccountExportScreen {...props} />);
    expect(screen.getByTestId("export-button")).toBeTruthy();
  });

  it("export button has correct accessibility label", () => {
    render(<DisabledAccountExportScreen {...props} />);
    const button = screen.getByTestId("export-button");
    expect(button.props.accessibilityLabel).toContain("Export");
  });

  it("account disabled message has role=alert", () => {
    render(<DisabledAccountExportScreen {...props} />);
    const alertBox = screen.getByLabelText("Your account has been disabled");
    expect(alertBox).toBeTruthy();
  });

  it("shows pending data notice", () => {
    render(<DisabledAccountExportScreen {...props} />);
    expect(screen.getByText("You have unsynced data")).toBeTruthy();
  });

  it("calls expo-file-system and expo-sharing on export", async () => {
    // Assert on expo-file-system/legacy — that's the module the component calls.
    // moduleNameMapper points this to __mocks__/expo-file-system-legacy.js.
    const FileSystem = require("expo-file-system/legacy") as {
      writeAsStringAsync: jest.Mock;
    };
    const Sharing = require("expo-sharing") as {
      shareAsync: jest.Mock;
    };

    render(<DisabledAccountExportScreen {...props} />);

    fireEvent.press(screen.getByTestId("export-button"));

    await waitFor(() => {
      expect(FileSystem.writeAsStringAsync).toHaveBeenCalled();
      expect(Sharing.shareAsync).toHaveBeenCalled();
    });
  });

  it("shows success message after export", async () => {
    render(<DisabledAccountExportScreen {...props} />);

    fireEvent.press(screen.getByTestId("export-button"));

    await waitFor(() => {
      expect(screen.getByText(/export shared successfully/i)).toBeTruthy();
    });
  });

  it("export JSON includes correct structure keys", async () => {
    const FileSystem = require("expo-file-system/legacy") as {
      writeAsStringAsync: jest.Mock;
    };
    FileSystem.writeAsStringAsync.mockClear();

    render(<DisabledAccountExportScreen {...props} />);
    fireEvent.press(screen.getByTestId("export-button"));

    await waitFor(() => {
      expect(FileSystem.writeAsStringAsync).toHaveBeenCalled();
    });

    const calls = FileSystem.writeAsStringAsync.mock.calls;
    const [, content] = calls[calls.length - 1] as [string, string];
    const exportData = JSON.parse(content) as Record<string, unknown>;

    expect(exportData["export_format_version"]).toBe(1);
    expect(exportData["tenant_id"]).toBe("tenant-001");
    expect(exportData["user_id"]).toBe("user-001");
    expect(exportData["records"]).toBeDefined();
    const records = exportData["records"] as Record<string, unknown>;
    expect(records["time_entries"]).toBeDefined();
    expect(records["expenses"]).toBeDefined();
    expect(records["photos"]).toBeDefined();
    expect(records["change_orders"]).toBeDefined();
    expect(records["loto_checks"]).toBeDefined();
    expect(records["job_status_changes"]).toBeDefined();
    expect(records["job_notes"]).toBeDefined();
  });
});
