/**
 * Voice Persona Types — FE-B12
 *
 * Location: apps/web/src/features/voice-persona/types.ts
 */

export type VoicePersonaTone = "conservative" | "balanced" | "playful";

export interface VoicePersonaToneEffectiveResponse {
  effective_tone: VoicePersonaTone;
  effective_scope: "user" | "tenant" | "system";
  user_override: VoicePersonaTone | null;
  tenant_default: VoicePersonaTone | null;
  system_default: "balanced";
  user_override_allowed: boolean;
  available_tones: VoicePersonaTone[];
  preview_audio_urls: Record<VoicePersonaTone, string>;
}

export interface VoicePersonaToneTenantResponse {
  tenant_default: VoicePersonaTone | null;
  tenant_default_scope: "tenant" | "system";
  system_default: "balanced";
  user_override_policy: boolean;
  available_tones: VoicePersonaTone[];
  preview_audio_urls: Record<VoicePersonaTone, string>;
}

export interface VoicePersonaToneCardProps {
  tone: VoicePersonaTone;
  label: string;
  description: string;
  isSelected: boolean;
  isTeamDefault: boolean;
  previewAudioUrl: string;
  onSelect: () => void;
  disabled?: boolean;
}

export type TonePreviewState =
  | "idle"
  | "loading"
  | "playing"
  | "ended"
  | "error";

export const TONE_LABELS: Record<VoicePersonaTone, string> = {
  conservative: "Conservative",
  balanced: "Balanced",
  playful: "Playful",
};

export const TONE_DESCRIPTIONS: Record<VoicePersonaTone, string> = {
  conservative:
    "Formal and precise. Best for enterprise clients who prefer professional communication.",
  balanced:
    "Friendly yet professional. The recommended setting for most contractors.",
  playful:
    "Warm and conversational. Great for building rapport with residential customers.",
};
