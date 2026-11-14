/**
 * VoicePersonaTonePicker — Web component
 *
 * Location: apps/web/src/features/voice-persona/components/VoicePersonaTonePicker.tsx
 *
 * Renders three tone cards (conservative / balanced / playful).
 * Each card has a "▶ Hear preview" button (TonePreviewButton).
 * Selecting a tone commits immediately (saveMode='blur' pattern).
 *
 * Design doc Section H token audit:
 * - Selected card: brand-500 2px border
 * - Unselected card: neutral-200 1px border
 * - Team default annotation: neutral-100 bg, neutral-600 text
 * - (your preference) annotation: brand-50 bg, brand-700 text
 *
 * RULE: Audio uses HTML5 <audio> element — not a new system.
 * RULE: One preview plays at a time (shared currentlyPlayingRef).
 */

"use client";

import React, { useRef, useState } from "react";
import type {
  VoicePersonaTone,
  VoicePersonaToneEffectiveResponse,
  TonePreviewState,
} from "../types";
import { TONE_LABELS, TONE_DESCRIPTIONS } from "../types";

// ─── Tone Preview Button ──────────────────────────────────────────────────────

function TonePreviewButton({
  previewUrl,
  currentlyPlayingRef,
  tone,
}: {
  previewUrl: string;
  currentlyPlayingRef: React.MutableRefObject<HTMLAudioElement | null>;
  tone: VoicePersonaTone;
}) {
  const [state, setState] = useState<TonePreviewState>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handlePlay = () => {
    // Pause any currently playing audio
    if (
      currentlyPlayingRef.current &&
      currentlyPlayingRef.current !== audioRef.current
    ) {
      currentlyPlayingRef.current.pause();
      currentlyPlayingRef.current = null;
    }

    if (state === "playing" && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setState("idle");
      currentlyPlayingRef.current = null;
      return;
    }

    setState("loading");
    const audio = new Audio(previewUrl);
    audioRef.current = audio;
    currentlyPlayingRef.current = audio;

    audio.oncanplaythrough = () => {
      setState("playing");
      void audio.play().catch(() => setState("error"));
    };

    audio.onended = () => {
      setState("ended");
      currentlyPlayingRef.current = null;
    };

    audio.onerror = () => {
      setState("error");
      currentlyPlayingRef.current = null;
    };

    audio.load();
  };

  const icon =
    state === "playing"
      ? "⏸"
      : state === "loading"
        ? "⏳"
        : state === "error"
          ? "⚠"
          : "▶";
  const label =
    state === "playing"
      ? "Pause preview"
      : state === "loading"
        ? "Loading preview..."
        : state === "error"
          ? "Preview unavailable"
          : "Hear preview";

  return (
    <button
      type="button"
      onClick={handlePlay}
      disabled={state === "loading" || state === "error"}
      aria-label={`${label} for ${TONE_LABELS[tone]} tone`}
      className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-brand-600 focus:outline-none focus:underline disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      data-testid={`tone-preview-${tone}`}
    >
      <span aria-hidden="true">{icon}</span>
      <span>{state === "error" ? "Preview unavailable" : label}</span>
    </button>
  );
}

// ─── Tone Card ────────────────────────────────────────────────────────────────

function VoicePersonaToneCard({
  tone,
  isSelected,
  isTeamDefault,
  hasUserOverride,
  previewAudioUrl,
  onSelect,
  disabled,
  currentlyPlayingRef,
}: {
  tone: VoicePersonaTone;
  isSelected: boolean;
  isTeamDefault: boolean;
  hasUserOverride: boolean;
  previewAudioUrl: string;
  onSelect: () => void;
  disabled?: boolean;
  currentlyPlayingRef: React.MutableRefObject<HTMLAudioElement | null>;
}) {
  return (
    <div
      className={`relative rounded-xl p-5 transition-all cursor-pointer focus-within:ring-2 focus-within:ring-brand-600 focus-within:ring-offset-1 ${
        isSelected
          ? "border-2 border-brand-500 bg-brand-50/30"
          : "border border-neutral-200 hover:border-neutral-300"
      } ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
      data-testid={`tone-card-${tone}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-neutral-900">
              {TONE_LABELS[tone]}
            </h3>
            {isSelected && (
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                  hasUserOverride
                    ? "bg-brand-50 text-brand-700"
                    : "bg-neutral-100 text-neutral-600"
                }`}
              >
                {hasUserOverride ? "your preference" : "active"}
              </span>
            )}
            {isTeamDefault && (
              <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-600">
                team default
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-neutral-500 leading-relaxed">
            {TONE_DESCRIPTIONS[tone]}
          </p>
          <div className="mt-2">
            <TonePreviewButton
              previewUrl={previewAudioUrl}
              tone={tone}
              currentlyPlayingRef={currentlyPlayingRef}
            />
          </div>
        </div>

        {/* Select button */}
        {!isSelected && !disabled && (
          <button
            type="button"
            onClick={onSelect}
            className="flex-shrink-0 rounded-md px-3 py-1.5 text-xs font-medium text-brand-600 border border-brand-200 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 transition-colors"
            data-testid={`select-tone-${tone}`}
            aria-label={`Use ${TONE_LABELS[tone]} voice tone`}
          >
            Use this tone
          </button>
        )}

        {isSelected && (
          <div
            className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-500 flex items-center justify-center"
            aria-label="Selected"
          >
            <svg
              className="w-3 h-3 text-white"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                d="M5 13l4 4L19 7"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Picker ──────────────────────────────────────────────────────────────

const TONE_ORDER: VoicePersonaTone[] = ["conservative", "balanced", "playful"];

export function VoicePersonaTonePicker({
  data,
  onSelect,
  onRevert,
  isPending,
  error,
}: {
  data: VoicePersonaToneEffectiveResponse;
  onSelect: (tone: VoicePersonaTone) => void;
  onRevert: () => void;
  isPending: boolean;
  error?: Error | null;
}) {
  const currentlyPlayingRef = useRef<HTMLAudioElement | null>(null);

  const userOverrideAllowed = data.user_override_allowed;
  const effectiveTone = data.effective_tone;
  const userOverride = data.user_override;
  const tenantDefault = data.tenant_default;

  return (
    <div
      className="flex flex-col gap-4"
      data-testid="voice-persona-tone-picker"
    >
      {!userOverrideAllowed && (
        <div className="rounded-md bg-neutral-50 border border-neutral-200 px-4 py-3 text-sm text-neutral-600">
          Your team has set a single voice tone. Contact your owner to change
          it.
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-md bg-fault-50 border border-fault-200 px-4 py-3 text-sm text-fault-700"
        >
          {error.message}
        </div>
      )}

      <div className="flex flex-col gap-3">
        {TONE_ORDER.map((tone) => (
          <VoicePersonaToneCard
            key={tone}
            tone={tone}
            isSelected={effectiveTone === tone}
            isTeamDefault={tenantDefault === tone}
            hasUserOverride={userOverride === tone}
            previewAudioUrl={data.preview_audio_urls[tone]}
            onSelect={() => onSelect(tone)}
            disabled={!userOverrideAllowed || isPending}
            currentlyPlayingRef={currentlyPlayingRef}
          />
        ))}
      </div>

      {/* Revert to tenant default */}
      {userOverride && (
        <button
          type="button"
          onClick={onRevert}
          disabled={isPending}
          className="self-start text-sm text-brand-600 hover:text-brand-800 focus:outline-none focus:underline disabled:opacity-50"
          data-testid="revert-to-tenant-default"
        >
          Match team default
        </button>
      )}
    </div>
  );
}
