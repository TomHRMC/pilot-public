/**
 * Voltage Drop Screen integration tests (MOB-B4)
 *
 * Location: apps/mobile/__tests__/batch_mob_b4/voltage-drop.integration.test.tsx
 *
 * Tests VoltageDropScreen form, online API call (MSW), offline banner,
 * and CalcResultDisplay pass/fail rendering.
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import NetInfo from "@react-native-community/netinfo";
import { VoltageDropScreen } from "../../features/nec-calcs/components/VoltageDrop/VoltageDropScreen";

jest.mock("expo-router", () => ({
  router: { push: jest.fn(), back: jest.fn() },
  useRouter: () => require("expo-router").router,
}));

// Mock NetInfo — default to online
jest.mock("@react-native-community/netinfo", () => ({
  __esModule: true,
  default: {
    fetch: jest.fn().mockResolvedValue({
      isConnected: true,
      isInternetReachable: true,
    }),
  },
}));

// Mock WatermelonDB database
jest.mock("../../database", () => ({
  database: {
    write: jest.fn().mockResolvedValue(undefined),
    get: jest.fn().mockReturnValue({
      create: jest.fn().mockResolvedValue({}),
    }),
  },
}));

// Use wildcard URL pattern — same pattern as all other integration tests in this project
const voltageDropFailResult = {
  log_id: "test-log-001",
  calc_type: "voltage_drop",
  result: {
    calc_type: "voltage_drop",
    result_value: 7.902,
    is_compliant: false,
    nec_article: "NEC 210.19(A)(1)",
    nec_citation:
      "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
    voltage_drop: 7.902,
    voltage_drop_pct: 6.585,
    wire_gauge: "12",
    amperage: 20,
    distance_feet: 100,
    voltage: 120,
    phase: 1,
  },
  nec_guide_version: "2023",
  nec_citation:
    "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
};

const voltageDropPassResult = {
  ...voltageDropFailResult,
  result: {
    ...voltageDropFailResult.result,
    result_value: 0.987,
    is_compliant: true,
    voltage_drop: 0.987,
    voltage_drop_pct: 0.823,
  },
};

const server = setupServer(
  http.post("*/api/v1/nec/calculate", () => {
    return HttpResponse.json(voltageDropFailResult, { status: 201 });
  }),
);

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeQC()}>{children}</QueryClientProvider>
  );
}

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
  // Reset NetInfo mock to online by default after each test
  (NetInfo.fetch as jest.Mock).mockResolvedValue({
    isConnected: true,
    isInternetReachable: true,
  });
});
afterAll(() => server.close());

describe("VoltageDropScreen", () => {
  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  it("renders the form with all expected inputs", () => {
    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    expect(screen.getByTestId("input-amperage")).toBeTruthy();
    expect(screen.getByTestId("input-distance")).toBeTruthy();
    expect(screen.getByTestId("input-voltage")).toBeTruthy();
    expect(screen.getByTestId("phase-single")).toBeTruthy();
    expect(screen.getByTestId("phase-three")).toBeTruthy();
    expect(screen.getByTestId("calculate-button")).toBeTruthy();
  });

  it("renders back navigation button", () => {
    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    expect(screen.getByTestId("back-button")).toBeTruthy();
  });

  // ---------------------------------------------------------------------------
  // Online path — API called, result displayed
  // ---------------------------------------------------------------------------

  it("online: submit form → API called → FAIL result displayed", async () => {
    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    fireEvent.changeText(screen.getByTestId("input-amperage"), "20");
    fireEvent.changeText(screen.getByTestId("input-distance"), "100");

    await act(async () => {
      fireEvent.press(screen.getByTestId("calculate-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("voltage-drop-result")).toBeTruthy();
    });

    // Should show FAIL badge
    expect(screen.getByTestId("result-fail-badge")).toBeTruthy();
  });

  it("online: OfflineBanner NOT shown when API call succeeds", async () => {
    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    fireEvent.changeText(screen.getByTestId("input-amperage"), "20");
    fireEvent.changeText(screen.getByTestId("input-distance"), "100");

    await act(async () => {
      fireEvent.press(screen.getByTestId("calculate-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("voltage-drop-result")).toBeTruthy();
    });

    // isOfflineCalc should be false after successful API call
    expect(screen.queryByTestId("offline-banner")).toBeNull();
  });

  // ---------------------------------------------------------------------------
  // Offline path — TypeScript engine used, OfflineBanner shown
  // ---------------------------------------------------------------------------

  it("offline: OfflineBanner shown when device is offline", async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValueOnce({
      isConnected: false,
      isInternetReachable: false,
    });

    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    fireEvent.changeText(screen.getByTestId("input-amperage"), "20");
    fireEvent.changeText(screen.getByTestId("input-distance"), "100");

    await act(async () => {
      fireEvent.press(screen.getByTestId("calculate-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("offline-banner")).toBeTruthy();
    });

    expect(
      screen.getByText("⚠️  Offline — using NEC 2023 code formulas"),
    ).toBeTruthy();
  });

  it("offline: TypeScript engine result displayed (no API call)", async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValueOnce({
      isConnected: false,
      isInternetReachable: false,
    });

    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    fireEvent.changeText(screen.getByTestId("input-amperage"), "20");
    fireEvent.changeText(screen.getByTestId("input-distance"), "100");

    await act(async () => {
      fireEvent.press(screen.getByTestId("calculate-button"));
    });

    await waitFor(() => {
      // Offline TS result: 20A, 100ft, 12 AWG (default), 120V, phase 1 → 6.58% → FAIL
      expect(screen.getByTestId("result-fail-badge")).toBeTruthy();
    });
  });

  // ---------------------------------------------------------------------------
  // API failure → fallback to offline
  // ---------------------------------------------------------------------------

  it("API 500 error → fallback to offline engine (OfflineBanner shown)", async () => {
    server.use(
      http.post("*/api/v1/nec/calculate", () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 });
      }),
    );

    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    fireEvent.changeText(screen.getByTestId("input-amperage"), "20");
    fireEvent.changeText(screen.getByTestId("input-distance"), "100");

    await act(async () => {
      fireEvent.press(screen.getByTestId("calculate-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("offline-banner")).toBeTruthy();
    });
  });

  // ---------------------------------------------------------------------------
  // CalcResultDisplay pass/fail
  // ---------------------------------------------------------------------------

  it("CalcResultDisplay shows '✓ PASS' when is_compliant=true", async () => {
    server.use(
      http.post("*/api/v1/nec/calculate", () => {
        return HttpResponse.json(voltageDropPassResult, { status: 201 });
      }),
    );

    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    fireEvent.changeText(screen.getByTestId("input-amperage"), "5");
    fireEvent.changeText(screen.getByTestId("input-distance"), "50");

    await act(async () => {
      fireEvent.press(screen.getByTestId("calculate-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("result-pass-badge")).toBeTruthy();
    });
  });

  it("CalcResultDisplay shows '✗ FAIL' when is_compliant=false", async () => {
    render(
      <Wrapper>
        <VoltageDropScreen />
      </Wrapper>,
    );

    fireEvent.changeText(screen.getByTestId("input-amperage"), "20");
    fireEvent.changeText(screen.getByTestId("input-distance"), "100");

    await act(async () => {
      fireEvent.press(screen.getByTestId("calculate-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("result-fail-badge")).toBeTruthy();
    });
  });
});
