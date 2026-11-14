/**
 * /settings/voice-ai — index redirect
 *
 * Redirects to the Persona & Tone sub-page.
 */

import { redirect } from "next/navigation";

export default function VoiceAiIndexPage() {
  redirect("/settings/voice-ai/persona-tone");
}
