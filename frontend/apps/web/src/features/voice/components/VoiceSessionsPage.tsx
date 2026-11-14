"use client";

/**
 * VoiceSessionsPage — voice session list
 *
 * Location: apps/web/src/features/voice/components/VoiceSessionsPage.tsx
 *
 * Lists past voice sessions. "+ New Session" creates and navigates to new session.
 */

import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { LoadingState, EmptyState, ErrorState } from "@pilot/ui/states";
import Link from "next/link";
import { useVoiceSessions } from "../hooks/useVoiceSessions";
import type { VoiceSession } from "../hooks/useVoiceSessions";

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function VoiceSessionsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useVoiceSessions(20);

  const createSession = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/api/v1/voice/sessions/");
      return res.data as { session_id: string };
    },
    onSuccess: (newSession) => {
      void queryClient.invalidateQueries({ queryKey: ["voice-sessions"] });
      void router.push(`/voice/${newSession.session_id}`);
    },
  });

  return (
    <div className="flex flex-col h-full bg-neutral-50">
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-neutral-200">
        <h1 className="text-h1 text-neutral-900">Voice Sessions</h1>
        <button
          type="button"
          onClick={() => createSession.mutate()}
          disabled={createSession.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-body-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          data-testid="new-session-btn"
        >
          {createSession.isPending ? "Creating…" : "+ New Session"}
        </button>
      </header>

      <main className="flex-1 px-6 py-6 max-w-3xl w-full mx-auto">
        {isLoading && <LoadingState type="inline" label="Loading sessions…" />}
        {isError && (
          <ErrorState
            type="server"
            title="Failed to load sessions"
            description="Unable to fetch voice session history."
          />
        )}
        {!isLoading &&
          !isError &&
          (!data?.sessions || data.sessions.length === 0) && (
            <EmptyState
              type="no-data"
              title="No voice sessions yet"
              description="Start your first voice session to begin."
              ctaLabel="+ New Session"
              onCta={() => createSession.mutate()}
            />
          )}
        {!isLoading &&
          !isError &&
          data?.sessions &&
          data.sessions.length > 0 && (
            <ul className="space-y-2">
              {data.sessions.map((session: VoiceSession) => (
                <li key={session.session_id}>
                  <Link
                    href={`/voice/${session.session_id}`}
                    className="flex items-center justify-between rounded-lg border border-neutral-200 bg-white px-4 py-3 hover:border-brand-300 hover:bg-brand-50"
                    data-testid={`session-row-${session.session_id}`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="shrink-0 text-caption font-medium text-neutral-400">
                          #{session.session_number}
                        </span>
                        <p className="truncate text-body-sm font-medium text-neutral-900">
                          {session.title ?? "Untitled session"}
                        </p>
                      </div>
                      <p className="mt-0.5 text-caption text-neutral-400">
                        {session.message_count} message
                        {session.message_count !== 1 ? "s" : ""} ·{" "}
                        {formatDate(session.created_at)}
                      </p>
                    </div>
                    <span className="ml-3 text-neutral-300">→</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
      </main>
    </div>
  );
}
