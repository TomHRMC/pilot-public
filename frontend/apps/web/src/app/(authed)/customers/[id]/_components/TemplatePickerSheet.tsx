/**
 * TemplatePickerSheet — Web template selection panel
 *
 * Location: apps/web/src/app/(authed)/customers/[id]/_components/TemplatePickerSheet.tsx
 *
 * Renders a sheet/drawer with 2×3 template card grid.
 * Channel override affordance above grid.
 * Composes usePreviewBeforeSend() for the preview → send flow.
 *
 * Online-only: blocks send when offline (§G3).
 * Zero hardcoded design values.
 */

"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePreviewBeforeSend } from "@pilot/ui";
import { ErrorState, LoadingState } from "@pilot/ui/states";
import type { CommTemplateTypeResponse } from "@pilot/ui";

// ── Template icon map ─────────────────────────────────────────────────────────

const TEMPLATE_ICONS: Record<string, string> = {
  on_my_way: "🚗",
  running_late: "⏰",
  arrived: "📍",
  job_complete: "✅",
  appointment_reminder: "📅",
  follow_up: "👋",
};

// ── API ───────────────────────────────────────────────────────────────────────

async function fetchTemplates(): Promise<CommTemplateTypeResponse[]> {
  const res = await fetch(
    "/api/v1/communications/comm-template-types?initiator=tech",
  );
  if (!res.ok) throw new Error("Failed to load templates");
  const data = (await res.json()) as { items: CommTemplateTypeResponse[] };
  return data.items;
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface TemplatePickerSheetProps {
  customerId: string;
  jobId?: string;
  onClose: () => void;
  onSendSuccess: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function TemplatePickerSheet({
  customerId,
  jobId,
  onClose,
  onSendSuccess,
}: TemplatePickerSheetProps) {
  const [channelOverride, setChannelOverride] = useState<
    "sms" | "email" | null
  >(null);
  const [isOffline, setIsOffline] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  // Online guard (§G3: online-only for customer comms)
  useEffect(() => {
    function updateOnlineStatus() {
      setIsOffline(!navigator.onLine);
    }
    updateOnlineStatus();
    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);
    return () => {
      window.removeEventListener("online", updateOnlineStatus);
      window.removeEventListener("offline", updateOnlineStatus);
    };
  }, []);

  const {
    data: templates,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["comm-template-types"],
    queryFn: fetchTemplates,
    staleTime: 5 * 60 * 1000,
  });

  const {
    preview,
    MessagePreviewModal,
    isPreviewLoading,
    sendError: hookSendError,
  } = usePreviewBeforeSend({
    onSendSuccess: () => {
      onSendSuccess();
    },
    onSendError: (err) => {
      if (err.message === "QUOTA_EXHAUSTED") {
        setSendError("Monthly SMS quota reached — contact your account owner");
      } else {
        setSendError(err.message);
      }
    },
  });

  async function handleTemplateSelect(template: CommTemplateTypeResponse) {
    if (isOffline) return;
    setSendError(null);
    try {
      await preview({
        mode: "template",
        customerId,
        templateCode: template.code,
        jobId,
        variables: {},
        channelOverride,
      });
    } catch (err) {
      if (err instanceof Error && err.message === "OFFLINE") {
        setIsOffline(true);
      } else {
        setSendError(err instanceof Error ? err.message : "Preview failed");
      }
    }
  }

  return (
    /* Sheet backdrop */
    <div
      className="fixed inset-0 z-40 flex justify-end bg-neutral-900/30"
      data-testid="template-picker-sheet"
    >
      {/* Sheet panel */}
      <div className="flex h-full w-full max-w-lg flex-col bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
          <h2 className="text-h2 font-medium text-neutral-900">Send message</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Offline guard */}
        {isOffline && (
          <div className="p-4">
            <ErrorState
              type="network"
              title="No internet connection"
              description="Message send requires internet connection. Please reconnect and try again."
            />
          </div>
        )}

        {/* Channel override */}
        {!isOffline && (
          <div className="border-b border-neutral-100 px-6 py-3">
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center rounded-full bg-brand-50 px-2 py-0.5 text-caption font-medium text-brand-800">
                {channelOverride === "email" ? "✉️ Email" : "💬 SMS preferred"}
              </span>
              <button
                type="button"
                onClick={() =>
                  setChannelOverride((prev) =>
                    prev === "email" ? null : "email",
                  )
                }
                className="text-caption text-brand-600 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                data-testid="channel-override-link"
              >
                {channelOverride === "email"
                  ? "Use SMS instead →"
                  : "Send via email instead →"}
              </button>
            </div>
          </div>
        )}

        {/* Error display */}
        {(sendError ?? hookSendError) && (
          <div className="mx-6 mt-3 rounded-md bg-fault-50 px-4 py-3">
            <p className="text-body text-fault-800">
              {sendError ?? hookSendError?.message}
            </p>
          </div>
        )}

        {/* Template grid */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading && (
            <LoadingState type="inline" label="Loading templates…" />
          )}
          {isError && (
            <ErrorState
              type="server"
              title="Failed to load templates"
              description="Please try again"
            />
          )}
          {templates && (
            <div className="grid grid-cols-2 gap-3" data-testid="template-grid">
              {templates.map((template) => (
                <button
                  key={template.code}
                  type="button"
                  onClick={() => handleTemplateSelect(template)}
                  disabled={isOffline || isPreviewLoading}
                  className="flex flex-col items-start rounded-lg border border-neutral-200 bg-white p-4 text-left transition-colors hover:border-brand-400 hover:bg-brand-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
                  data-testid={`template-card-${template.code}`}
                  aria-label={template.name}
                >
                  <span className="mb-2 text-h2" aria-hidden="true">
                    {TEMPLATE_ICONS[template.code] ?? "📨"}
                  </span>
                  <span className="text-body font-medium text-neutral-900">
                    {template.name}
                  </span>
                  {template.description && (
                    <span className="mt-1 text-caption text-neutral-400 line-clamp-1">
                      {template.description}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Embedded MessagePreviewModal from hook */}
      <MessagePreviewModal onEdit={onClose} />
    </div>
  );
}
