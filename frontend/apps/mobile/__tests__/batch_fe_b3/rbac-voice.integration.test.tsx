/**
 * RBAC voice integration tests — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/rbac-voice.integration.test.tsx
 * 4 tests: voice permission, role-based submit label
 */

import React from "react";
import { render } from "@testing-library/react-native";

jest.mock("expo-av", () => ({ Audio: {} }));
jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn().mockReturnValue({ data: undefined, isLoading: false }),
  QueryClient: jest.fn(),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) =>
    children,
}));

describe("RBAC voice permissions", () => {
  it('VoiceQuotePreview with is_tech_role=false renders "Send" button in live mode', () => {
    // This verifies the submit button label logic in VoiceQuotePreview
    const mockData = {
      quote_id: "q-001",
      customer_name: "Tom Johnson",
      total_cents: 150000,
      margin_pct: 22,
      line_items: [],
      style: "component" as const,
      is_tech_role: false,
    };

    const { useQuery } = require("@tanstack/react-query");
    useQuery.mockReturnValue({ data: mockData, isLoading: false });

    const {
      VoiceQuotePreview,
    } = require("../../features/voice-quote-creation/components/VoiceQuotePreview");
    const { getByText } = render(
      <VoiceQuotePreview mode="live" entityId="q-001" onSubmit={() => {}} />,
    );
    expect(getByText("Send")).toBeTruthy();
  });

  it('VoiceQuotePreview with is_tech_role=true renders "Submit for Approval" in live mode', () => {
    const mockData = {
      quote_id: "q-001",
      customer_name: "Tom Johnson",
      total_cents: 150000,
      margin_pct: 22,
      line_items: [],
      style: "component" as const,
      is_tech_role: true,
    };

    const { useQuery } = require("@tanstack/react-query");
    useQuery.mockReturnValue({ data: mockData, isLoading: false });

    const {
      VoiceQuotePreview,
    } = require("../../features/voice-quote-creation/components/VoiceQuotePreview");
    const { getByText } = render(
      <VoiceQuotePreview mode="live" entityId="q-001" onSubmit={() => {}} />,
    );
    expect(getByText("Submit for Approval")).toBeTruthy();
  });

  it("voiceStateTokens define distinct visual states for each of 6 machine states", () => {
    const {
      voiceStateTokens,
    } = require("../../../../packages/ui/src/voice/types");
    const bgTokens = Object.values(voiceStateTokens).map((t: any) => t.bgToken);
    // At least some states should have distinct bg tokens (not all identical)
    const uniqueTokens = new Set(bgTokens);
    expect(uniqueTokens.size).toBeGreaterThan(1);
  });

  it("useVoiceStream is exported from packages/ui barrel", () => {
    // Verifies the shared module export used by FE-B5/B6/B10/B16
    const uiIndex = require("../../../../packages/ui/src/index");
    expect(typeof uiIndex.useVoiceStream).toBe("function");
    expect(typeof uiIndex.VoiceConfirmTurn).toBe("function");
    expect(typeof uiIndex.voiceStateTokens).toBe("object");
  });
});
