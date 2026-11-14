/**
 * Voice Persona MSW Handlers — FE-B12
 *
 * Location: apps/web/src/mocks/handlers/voicePersonaHandlers.ts
 *
 * Covers BE-B12 / A67:
 *  - GET  /api/v1/settings/voice-persona-tone
 *  - PUT  /api/v1/settings/voice-persona-tone
 *  - DELETE /api/v1/settings/voice-persona-tone
 *  - GET  /api/v1/settings/tenant/voice-persona-tone
 *  - PUT  /api/v1/settings/tenant/voice-persona-tone
 *  - DELETE /api/v1/settings/tenant/voice-persona-tone
 *  - PUT  /api/v1/settings/tenant/voice-persona-tone-user-override-allowed
 */

import { http, HttpResponse } from "msw";
import type {
  VoicePersonaToneEffectiveResponse,
  VoicePersonaTone,
} from "../../features/voice-persona/types";

const API = "/api/v1/settings";

const PREVIEW_AUDIO_URLS: Record<VoicePersonaTone, string> = {
  conservative:
    "https://cdn.example.com/voice-previews/conservative.mp3",
  balanced: "https://cdn.example.com/voice-previews/balanced.mp3",
  playful: "https://cdn.example.com/voice-previews/playful.mp3",
};

// Mutable state for test mutations
let currentUserOverride: VoicePersonaTone | null = null;
let userOverrideAllowed = true;

export const voicePersonaHandlers = [
  // GET user effective tone
  http.get(`${API}/voice-persona-tone`, () => {
    const effectiveTone: VoicePersonaTone = currentUserOverride ?? "balanced";
    const effectiveScope = currentUserOverride ? "user" : "tenant";

    const response: VoicePersonaToneEffectiveResponse = {
      effective_tone: effectiveTone,
      effective_scope: effectiveScope,
      user_override: currentUserOverride,
      tenant_default: "balanced",
      system_default: "balanced",
      user_override_allowed: userOverrideAllowed,
      available_tones: ["conservative", "balanced", "playful"],
      preview_audio_urls: PREVIEW_AUDIO_URLS,
    };
    return HttpResponse.json(response);
  }),

  // PUT user override
  http.put(`${API}/voice-persona-tone`, async ({ request }) => {
    if (!userOverrideAllowed) {
      return HttpResponse.json(
        { detail: "Your team has restricted voice tone. Contact your owner." },
        { status: 403 },
      );
    }
    const body = (await request.json()) as { value: VoicePersonaTone };
    currentUserOverride = body.value;
    return HttpResponse.json({
      setting_key: "voice_persona_tone",
      value: body.value,
      scope: "user",
      updated_at: new Date().toISOString(),
    });
  }),

  // DELETE user override (revert to tenant/system)
  http.delete(`${API}/voice-persona-tone`, () => {
    currentUserOverride = null;
    return new HttpResponse(null, { status: 204 });
  }),

  // GET tenant defaults
  http.get(`${API}/tenant/voice-persona-tone`, () => {
    return HttpResponse.json({
      tenant_default: "balanced",
      tenant_default_scope: "tenant",
      system_default: "balanced",
      user_override_policy: userOverrideAllowed,
      available_tones: ["conservative", "balanced", "playful"],
      preview_audio_urls: PREVIEW_AUDIO_URLS,
    });
  }),

  // PUT tenant default (owner only)
  http.put(`${API}/tenant/voice-persona-tone`, async ({ request }) => {
    const body = (await request.json()) as { value: VoicePersonaTone };
    return HttpResponse.json({
      setting_key: "voice_persona_tone_tenant_default",
      value: body.value,
      scope: "tenant",
      updated_at: new Date().toISOString(),
    });
  }),

  // DELETE tenant default
  http.delete(`${API}/tenant/voice-persona-tone`, () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // PUT user-override-allowed (owner only)
  http.put(
    `${API}/tenant/voice-persona-tone-user-override-allowed`,
    async ({ request }) => {
      const body = (await request.json()) as { value: boolean };
      userOverrideAllowed = body.value;
      return HttpResponse.json({
        setting_key: "voice_persona_tone_user_override_allowed",
        value: body.value,
        scope: "tenant",
        updated_at: new Date().toISOString(),
      });
    },
  ),
];
