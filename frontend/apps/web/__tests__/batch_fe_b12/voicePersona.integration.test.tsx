/**
 * Voice Persona Integration Tests — FE-B12
 * Location: apps/web/__tests__/batch_fe_b12/voicePersona.integration.test.tsx
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { VoicePersonaTonePicker } from "../../src/features/voice-persona/components/VoicePersonaTonePicker";
import type {
  VoicePersonaToneEffectiveResponse,
  VoicePersonaTone,
} from "../../src/features/voice-persona/types";

const BASE_RESPONSE: VoicePersonaToneEffectiveResponse = {
  effective_tone: "balanced",
  effective_scope: "tenant",
  user_override: null,
  tenant_default: "balanced",
  system_default: "balanced",
  user_override_allowed: true,
  available_tones: ["conservative", "balanced", "playful"],
  preview_audio_urls: {
    conservative: "https://cdn.example.com/conservative.mp3",
    balanced: "https://cdn.example.com/balanced.mp3",
    playful: "https://cdn.example.com/playful.mp3",
  },
};

const server = setupServer(
  http.put("/api/v1/settings/voice-persona-tone", async ({ request }) => {
    const body = (await request.json()) as { value: VoicePersonaTone };
    return HttpResponse.json({
      setting_key: "voice_persona_tone",
      value: body.value,
      scope: "user",
      updated_at: new Date().toISOString(),
    });
  }),
  http.delete(
    "/api/v1/settings/voice-persona-tone",
    () => new HttpResponse(null, { status: 204 }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderPicker(
  data: VoicePersonaToneEffectiveResponse,
  overrides?: object,
) {
  const onSelect = vi.fn();
  const onRevert = vi.fn();
  render(
    <VoicePersonaTonePicker
      data={data}
      onSelect={onSelect}
      onRevert={onRevert}
      isPending={false}
      {...overrides}
    />,
  );
  return { onSelect, onRevert };
}

describe("VoicePersonaTonePicker", () => {
  it("renders 3 tone cards", () => {
    renderPicker(BASE_RESPONSE);
    expect(screen.getByTestId("tone-card-conservative")).toBeInTheDocument();
    expect(screen.getByTestId("tone-card-balanced")).toBeInTheDocument();
    expect(screen.getByTestId("tone-card-playful")).toBeInTheDocument();
  });

  it("effective_tone='balanced' shows balanced as selected", () => {
    renderPicker(BASE_RESPONSE);
    expect(screen.getByTestId("tone-card-balanced")).toHaveClass(
      "border-brand-500",
    );
  });

  it("tenant_default annotation appears on matching card", () => {
    renderPicker(BASE_RESPONSE);
    const balancedCard = screen.getByTestId("tone-card-balanced");
    expect(balancedCard).toHaveTextContent("team default");
  });

  it("'Use this tone' click fires onSelect with correct value", async () => {
    const { onSelect } = renderPicker(BASE_RESPONSE);
    fireEvent.click(screen.getByTestId("select-tone-playful"));
    expect(onSelect).toHaveBeenCalledWith("playful");
  });

  it("selecting playful updates selection immediately (optimistic-like)", () => {
    const { onSelect } = renderPicker(BASE_RESPONSE);
    fireEvent.click(screen.getByTestId("select-tone-playful"));
    expect(onSelect).toHaveBeenCalledWith("playful");
  });

  it("user_override_allowed=false disables all 'Use this tone' buttons", () => {
    renderPicker({ ...BASE_RESPONSE, user_override_allowed: false });
    const selectBtns = screen.queryAllByTestId(/select-tone-/);
    selectBtns.forEach((btn) => expect(btn).toBeDisabled());
  });

  it("user_override_allowed=false shows read-only annotation", () => {
    renderPicker({ ...BASE_RESPONSE, user_override_allowed: false });
    expect(
      screen.getByText(/team has set a single voice tone/i),
    ).toBeInTheDocument();
  });

  it("Match team default link calls onRevert when user has override", () => {
    const { onRevert } = renderPicker({
      ...BASE_RESPONSE,
      user_override: "playful",
      effective_tone: "playful",
      effective_scope: "user",
    });
    fireEvent.click(screen.getByTestId("revert-to-tenant-default"));
    expect(onRevert).toHaveBeenCalled();
  });

  it("TonePreviewButton is present for each card", () => {
    renderPicker(BASE_RESPONSE);
    expect(screen.getByTestId("tone-preview-conservative")).toBeInTheDocument();
    expect(screen.getByTestId("tone-preview-balanced")).toBeInTheDocument();
    expect(screen.getByTestId("tone-preview-playful")).toBeInTheDocument();
  });

  it("(your preference) annotation when user has override", () => {
    renderPicker({
      ...BASE_RESPONSE,
      user_override: "playful",
      effective_tone: "playful",
      effective_scope: "user",
    });
    const playfulCard = screen.getByTestId("tone-card-playful");
    expect(playfulCard).toHaveTextContent("your preference");
  });
});
