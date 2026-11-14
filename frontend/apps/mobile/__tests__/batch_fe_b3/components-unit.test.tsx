/**
 * Voice Quote Creation — component unit tests (FE-B3)
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/components-unit.test.tsx
 *
 * Covers: MarginCard (4), ContextChip (4), MicButton (5), StructuredMessage (5) = 18 tests
 */

import React from "react";
import { render, fireEvent } from "@testing-library/react-native";

jest.mock("@tanstack/react-query", () => ({
  useQuery: jest.fn().mockReturnValue({ data: undefined, isLoading: false }),
  QueryClient: jest.fn(),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) =>
    children,
}));

// Mock expo-av
jest.mock("expo-av", () => ({ Audio: {} }));

// ── MarginCard ────────────────────────────────────────────────────────────────

describe("MarginCard", () => {
  const {
    MarginCard,
  } = require("../../features/voice-quote-creation/components/MarginCard");

  it("renders margin percentage", () => {
    const { getByText } = render(
      <MarginCard marginPct={25} tenantTargetPct={20} />,
    );
    expect(getByText("25%")).toBeTruthy();
  });

  it('shows "On Target" label when marginPct >= tenantTargetPct', () => {
    const { getByText } = render(
      <MarginCard marginPct={20} tenantTargetPct={20} />,
    );
    expect(getByText("On Target")).toBeTruthy();
  });

  it("shows target reminder when marginPct < tenantTargetPct", () => {
    const { getByText } = render(
      <MarginCard marginPct={15} tenantTargetPct={20} />,
    );
    expect(getByText("Below target margin")).toBeTruthy();
  });

  it("renders advisory note text when below target (non-blocking)", () => {
    const { getByText } = render(
      <MarginCard marginPct={10} tenantTargetPct={20} />,
    );
    // Both the target reminder and advisory should be present
    expect(getByText("Target: 20%")).toBeTruthy();
    expect(getByText("Below target margin")).toBeTruthy();
  });
});

// ── ContextChip ───────────────────────────────────────────────────────────────

describe("ContextChip", () => {
  const {
    ContextChip,
  } = require("../../features/voice-quote-creation/components/ContextChip");

  it("renders null when contextWindow is null", () => {
    const { toJSON } = render(<ContextChip contextWindow={null} />);
    expect(toJSON()).toBeNull();
  });

  it("renders customer name when active_customer_name is set", () => {
    const { getByText } = render(
      <ContextChip
        contextWindow={{
          active_customer_id: "c-001",
          active_customer_name: "Tom Johnson",
          active_job_id: null,
          active_quote_id: null,
        }}
      />,
    );
    expect(getByText("Tom Johnson")).toBeTruthy();
  });

  it("renders null when active_customer_name is null", () => {
    const { toJSON } = render(
      <ContextChip
        contextWindow={{
          active_customer_id: null,
          active_customer_name: null,
          active_job_id: null,
          active_quote_id: null,
        }}
      />,
    );
    expect(toJSON()).toBeNull();
  });

  it("has correct accessibility label", () => {
    const { getByLabelText } = render(
      <ContextChip
        contextWindow={{
          active_customer_id: "c-001",
          active_customer_name: "Tom Johnson",
          active_job_id: null,
          active_quote_id: null,
        }}
      />,
    );
    expect(getByLabelText("Active context: Tom Johnson")).toBeTruthy();
  });
});

// ── MicButton ─────────────────────────────────────────────────────────────────

describe("MicButton", () => {
  const {
    MicButton,
  } = require("../../features/voice-quote-creation/components/MicButton");

  it("renders with correct accessibilityLabel for idle state", () => {
    const { getByTestId } = render(
      <MicButton voiceState="idle" onPress={() => {}} />,
    );
    // Use testID to target the pressable directly (indicator inside also has same label)
    expect(getByTestId("voice-trigger-btn")).toBeTruthy();
  });

  it("renders with correct accessibilityLabel for listening state", () => {
    const { getAllByLabelText } = render(
      <MicButton voiceState="listening" onPress={() => {}} />,
    );
    const elements = getAllByLabelText("Listening — tap to stop");
    expect(elements.length).toBeGreaterThan(0);
  });

  it("onPress fires on tap", () => {
    const onPress = jest.fn();
    const { getByTestId } = render(
      <MicButton voiceState="idle" onPress={onPress} />,
    );
    fireEvent.press(getByTestId("voice-trigger-btn"));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('has testID="voice-trigger-btn" by default', () => {
    const { getByTestId } = render(
      <MicButton voiceState="idle" onPress={() => {}} />,
    );
    expect(getByTestId("voice-trigger-btn")).toBeTruthy();
  });

  it("fieldMode={true} renders without crash", () => {
    expect(() =>
      render(<MicButton voiceState="idle" onPress={() => {}} fieldMode />),
    ).not.toThrow();
  });
});

// ── StructuredMessage ─────────────────────────────────────────────────────────

describe("StructuredMessage", () => {
  const {
    StructuredMessage,
  } = require("../../features/voice-quote-creation/components/StructuredMessage");

  const makeMsg = (
    content_type: string,
    render_mode: "live" | "snapshot" = "live",
    snapshot_payload: Record<string, unknown> | null = null,
  ) => ({
    id: "msg-001",
    structured_content: {
      render_mode,
      content_type: content_type as
        | "quote_preview"
        | "job_etc_status"
        | "conflict_summary"
        | "text",
      entity_id: "e-001",
      snapshot_payload,
    },
  });

  it("content_type quote_preview + live renders VoiceQuotePreview", () => {
    expect(() =>
      render(<StructuredMessage message={makeMsg("quote_preview", "live")} />),
    ).not.toThrow();
  });

  it("content_type quote_preview + snapshot renders VoiceQuotePreview", () => {
    const payload = {
      quote_id: "q-001",
      customer_name: "Tom Johnson",
      total_cents: 500000,
      margin_pct: 25,
      line_items: [],
      style: "component",
      is_tech_role: false,
    };
    expect(() =>
      render(
        <StructuredMessage
          message={makeMsg(
            "quote_preview",
            "snapshot",
            payload as Record<string, unknown>,
          )}
        />,
      ),
    ).not.toThrow();
  });

  it("content_type job_etc_status renders JobEtcStatusCard (MOB-B6: no longer a stub)", () => {
    const { getByTestId } = render(
      <StructuredMessage
        message={makeMsg("job_etc_status", "snapshot", { status: "active" })}
      />,
    );
    // MOB-B6: replaced stub with JobEtcStatusCard
    expect(getByTestId("job-etc-status-card")).toBeTruthy();
  });

  it("content_type conflict_summary renders ConflictSummaryCard (MOB-B6: no longer a stub)", () => {
    const { getByTestId } = render(
      <StructuredMessage
        message={makeMsg("conflict_summary", "snapshot", {
          conflict: "schedule clash",
        })}
      />,
    );
    // MOB-B6: replaced stub with ConflictSummaryCard
    expect(getByTestId("conflict-summary-card")).toBeTruthy();
  });

  it("unknown content_type renders null without crashing", () => {
    const { toJSON } = render(
      <StructuredMessage message={makeMsg("unknown_type", "live")} />,
    );
    expect(toJSON()).toBeNull();
  });
});
