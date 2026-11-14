/**
 * Voice Persona Tone Page — FE-B12
 *
 * Location: apps/web/src/app/(authed)/settings/voice-ai/persona-tone/page.tsx
 *
 * Route: /settings/voice-ai/persona-tone
 */

"use client";

import React from "react";
import { VoicePersonaTonePicker } from "../../../../../features/voice-persona/components/VoicePersonaTonePicker";
import { useVoicePersonaTone } from "../../../../../features/voice-persona/hooks/useVoicePersonaTone";

export default function VoicePersonaTonePage() {
  const { data, isLoading, isError, isPending, setTone, revertTone, setError } =
    useVoicePersonaTone();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
        Failed to load voice persona settings. Please refresh the page.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-h2 font-semibold text-neutral-900">
          Voice AI tone
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Choose the communication style for your Voice AI assistant. Preview
          each tone before selecting.
        </p>
      </div>

      <VoicePersonaTonePicker
        data={data}
        onSelect={setTone}
        onRevert={revertTone}
        isPending={isPending}
        error={setError instanceof Error ? setError : null}
      />
    </div>
  );
}
