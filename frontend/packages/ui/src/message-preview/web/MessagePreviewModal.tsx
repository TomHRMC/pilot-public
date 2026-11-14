/**
 * MessagePreviewModal — Web (shadcn/ui Dialog)
 *
 * Location: packages/ui/src/message-preview/web/MessagePreviewModal.tsx
 *
 * Renders a centered dialog showing the server-rendered message preview.
 * Called by usePreviewBeforeSend() hook — consumers don't instantiate directly.
 *
 * IMPORTANT: Zero hardcoded design values. All colors/spacing from pilotPreset tokens.
 */

import React from "react";
import type {
  EditableVariableResponse,
  MessagePreviewModalProps,
} from "../types";
import { VoiceConfirmTurn } from "../../voice-confirm-turn";

// ── Helpers ───────────────────────────────────────────────────────────────────

function ChannelPill({
  channel,
  isOverridden,
}: {
  channel: "sms" | "email" | string;
  isOverridden: boolean;
}) {
  const isSms = channel === "sms";
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={[
          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-caption font-medium",
          isSms
            ? "bg-brand-50 text-brand-800"
            : "bg-neutral-100 text-neutral-600",
        ].join(" ")}
        aria-label={`Channel: ${channel}`}
      >
        {isSms ? (
          // Chat bubble icon
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 16 16"
            fill="currentColor"
            className="h-3 w-3"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M1 8a7 7 0 1 1 14 0A7 7 0 0 1 1 8Zm7.75-4.25a.75.75 0 0 0-1.5 0V8.5l-2.22-2.22a.75.75 0 0 0-1.06 1.06l3 3a.75.75 0 0 0 1.06 0l3-3a.75.75 0 0 0-1.06-1.06l-2.22 2.22V3.75Z"
              clipRule="evenodd"
            />
          </svg>
        ) : (
          // Envelope icon
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 16 16"
            fill="currentColor"
            className="h-3 w-3"
            aria-hidden="true"
          >
            <path d="M1.75 2A1.75 1.75 0 0 0 0 3.75v.443l8 4.8 8-4.8V3.75A1.75 1.75 0 0 0 14.25 2h-12.5ZM16 6.037l-7.608 4.565a.75.75 0 0 1-.784 0L0 6.037V12.25C0 13.216.784 14 1.75 14h12.5A1.75 1.75 0 0 0 16 12.25V6.037Z" />
          </svg>
        )}
        {isSms ? "SMS" : "Email"}
      </span>
      {isOverridden && (
        <span className="inline-flex items-center rounded-full bg-alert-50 px-2 py-0.5 text-caption font-medium text-alert-800">
          Channel overridden
        </span>
      )}
    </span>
  );
}

function EditableVariableChip({
  label,
  value,
  onEdit,
}: {
  label: string;
  value: unknown;
  onEdit?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onEdit}
      className="inline-flex items-center gap-1 rounded border border-dashed border-alert-400 bg-alert-50 px-2 py-0.5 text-caption text-alert-800 hover:bg-alert-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-alert-400"
      aria-label={`Edit ${label}: ${String(value)}`}
    >
      {label}: {String(value)}
    </button>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

/**
 * MessagePreviewModal (Web)
 *
 * Renders as a shadcn/ui-compatible centered dialog overlay.
 * All buttons are disabled while isSending is true.
 * voiceMode renders <VoiceConfirmTurn> in place of tap buttons.
 */
export function MessagePreviewModal({
  previewData,
  isOpen,
  onConfirm,
  onCancel,
  onEdit,
  isSending = false,
  voiceMode = false,
  onChannelOverride,
  smsSegmentCount,
  testID,
}: MessagePreviewModalProps) {
  if (!isOpen || !previewData) return null;

  const {
    rendered_body,
    rendered_subject,
    recipient_name,
    recipient_address,
    actual_channel,
    editable_variables,
  } = previewData;

  const isChannelOverridden =
    "channel_override_flag" in previewData
      ? Boolean(
          (previewData as { channel_override_flag?: boolean })
            .channel_override_flag,
        )
      : false;

  const sendLabel = `Send to ${recipient_name}`;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Message preview"
      data-testid={testID ?? "message-preview-modal"}
    >
      {/* Dialog panel */}
      <div className="relative w-full max-w-lg rounded-lg bg-white shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
          <h2 className="text-h2 font-medium text-neutral-900">
            Preview message
          </h2>
          <button
            type="button"
            onClick={onCancel}
            disabled={isSending}
            className="rounded p-1 text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 disabled:opacity-50"
            aria-label="Close preview"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 16 16"
              fill="currentColor"
              className="h-4 w-4"
              aria-hidden="true"
            >
              <path d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z" />
            </svg>
          </button>
        </div>

        {/* Recipient + channel row */}
        <div className="flex items-center justify-between border-b border-neutral-100 px-6 py-3">
          <div>
            <p className="text-caption text-neutral-400">To</p>
            <p className="text-body font-medium text-neutral-900">
              {recipient_name}
            </p>
            <p className="text-caption text-neutral-600">{recipient_address}</p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <ChannelPill
              channel={actual_channel}
              isOverridden={isChannelOverridden}
            />
            {onChannelOverride && (
              <button
                type="button"
                onClick={() =>
                  onChannelOverride(actual_channel === "sms" ? "email" : "sms")
                }
                disabled={isSending}
                className="text-caption text-brand-600 underline-offset-2 hover:underline disabled:opacity-50"
              >
                Change channel
              </button>
            )}
          </div>
        </div>

        {/* Subject line (email only) */}
        {rendered_subject && (
          <div className="border-b border-neutral-100 px-6 py-3">
            <p className="text-caption text-neutral-400">Subject</p>
            <p className="text-body text-neutral-900">{rendered_subject}</p>
          </div>
        )}

        {/* Message body */}
        <div className="px-6 py-4">
          <p className="text-caption mb-1 text-neutral-400">Message</p>
          <p
            className="whitespace-pre-wrap rounded-md bg-neutral-50 p-3 text-body text-neutral-900"
            aria-live="polite"
          >
            {rendered_body}
          </p>

          {/* Editable variable chips */}
          {editable_variables.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {editable_variables.map((v: EditableVariableResponse) => (
                <EditableVariableChip
                  key={v.name}
                  label={v.label}
                  value={v.value}
                />
              ))}
            </div>
          )}
        </div>

        {/* SMS segment count */}
        {actual_channel === "sms" && smsSegmentCount !== undefined && (
          <div className="px-6 pb-2">
            <p className="text-caption text-neutral-400">
              {smsSegmentCount} SMS segment{smsSegmentCount !== 1 ? "s" : ""}
            </p>
          </div>
        )}

        {/* Footer actions */}
        <div className="border-t border-neutral-200 px-6 py-4">
          {voiceMode ? (
            <VoiceConfirmTurn
              prompt={`Send "${rendered_body.slice(0, 60)}${rendered_body.length > 60 ? "…" : ""}" to ${recipient_name}?`}
              onConfirm={onConfirm}
              onCancel={onCancel}
              isProcessing={isSending}
              testID="voice-confirm-in-preview"
            />
          ) : (
            <div className="flex gap-3">
              {onEdit && (
                <button
                  type="button"
                  onClick={onEdit}
                  disabled={isSending}
                  className="flex-1 rounded-md border border-neutral-200 bg-white px-4 py-2 text-body font-medium text-neutral-800 hover:bg-neutral-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 disabled:opacity-50"
                  data-testid="preview-edit-btn"
                >
                  Edit
                </button>
              )}
              <button
                type="button"
                onClick={onCancel}
                disabled={isSending}
                className="flex-1 rounded-md border border-neutral-200 bg-white px-4 py-2 text-body font-medium text-neutral-800 hover:bg-neutral-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 disabled:opacity-50"
                data-testid="preview-cancel-btn"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onConfirm}
                disabled={isSending}
                className="flex-[2] rounded-md bg-brand-600 px-4 py-2 text-body font-medium text-white hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:opacity-50"
                aria-busy={isSending}
                data-testid="preview-send-btn"
              >
                {isSending ? "Sending…" : sendLabel}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
