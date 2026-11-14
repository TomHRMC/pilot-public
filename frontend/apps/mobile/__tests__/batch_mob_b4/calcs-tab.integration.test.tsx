/**
 * Calcs Tab integration tests (MOB-B4)
 *
 * Location: apps/mobile/__tests__/batch_mob_b4/calcs-tab.integration.test.tsx
 *
 * Tests CalcsMenuScreen renders all menu rows and navigation works.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";

import { router } from "expo-router";
import { CalcsMenuScreen } from "../../features/nec-calcs/components/CalcsMenuScreen";

jest.mock("expo-router", () => ({
  router: { push: jest.fn(), back: jest.fn() },
  useRouter: () => require("expo-router").router,
}));

const mockRouterPush = router.push as jest.Mock;

describe("CalcsMenuScreen (calcs tab)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders Calcs title heading", () => {
    render(<CalcsMenuScreen />);
    expect(screen.getByText("Calcs")).toBeTruthy();
  });

  it("does NOT render centered 'Calcs' stub (stub was replaced)", () => {
    // The old stub had style={{ flex:1, alignItems:'center', justifyContent:'center' }}
    // The new CalcsMenuScreen has a title row — verify menu rows are present instead
    render(<CalcsMenuScreen />);
    // Menu rows should be present
    expect(screen.getByTestId("menu-voltage-drop")).toBeTruthy();
    expect(screen.getByTestId("menu-conduit-fill")).toBeTruthy();
    expect(screen.getByTestId("menu-ampacity")).toBeTruthy();
    expect(screen.getByTestId("menu-saved-calcs")).toBeTruthy();
    expect(screen.getByTestId("menu-nec-reference")).toBeTruthy();
  });

  it("renders 4 navigable rows + 1 disabled NEC Reference row", () => {
    render(<CalcsMenuScreen />);

    expect(screen.getByText("Voltage Drop Calculator")).toBeTruthy();
    expect(screen.getByText("Conduit Fill Calculator")).toBeTruthy();
    expect(screen.getByText("Ampacity Calculator")).toBeTruthy();
    expect(screen.getByText("Saved Calculations")).toBeTruthy();
    expect(screen.getByText("NEC 2023 Reference")).toBeTruthy();
    expect(screen.getByText("Coming soon")).toBeTruthy();
  });

  it("tapping Voltage Drop → router.push to calcs/voltage-drop", () => {
    render(<CalcsMenuScreen />);
    fireEvent.press(screen.getByTestId("menu-voltage-drop"));
    expect(mockRouterPush).toHaveBeenCalledWith(
      expect.stringContaining("voltage-drop"),
    );
  });

  it("tapping Conduit Fill → router.push to calcs/conduit-fill", () => {
    render(<CalcsMenuScreen />);
    fireEvent.press(screen.getByTestId("menu-conduit-fill"));
    expect(mockRouterPush).toHaveBeenCalledWith(
      expect.stringContaining("conduit-fill"),
    );
  });

  it("tapping Ampacity → router.push to calcs/ampacity", () => {
    render(<CalcsMenuScreen />);
    fireEvent.press(screen.getByTestId("menu-ampacity"));
    expect(mockRouterPush).toHaveBeenCalledWith(
      expect.stringContaining("ampacity"),
    );
  });

  it("tapping Saved Calculations → router.push to calcs/saved-calcs", () => {
    render(<CalcsMenuScreen />);
    fireEvent.press(screen.getByTestId("menu-saved-calcs"));
    expect(mockRouterPush).toHaveBeenCalledWith(
      expect.stringContaining("saved-calcs"),
    );
  });

  it("NEC Reference row is not a pressable (no navigation)", () => {
    render(<CalcsMenuScreen />);
    // The NEC reference row is a View (disabled), not a Pressable
    // Attempting to tap it should NOT call router.push
    const necRefRow = screen.getByTestId("menu-nec-reference");
    fireEvent.press(necRefRow);
    // router.push should NOT have been called for nec-reference
    expect(mockRouterPush).not.toHaveBeenCalledWith(
      expect.stringContaining("nec-reference"),
    );
  });
});
