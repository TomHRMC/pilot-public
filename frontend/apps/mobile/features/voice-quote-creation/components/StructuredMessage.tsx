/**
 * StructuredMessage — renders structured_content_json for a ConversationMessage
 *
 * Location: apps/mobile/features/voice-quote-creation/components/StructuredMessage.tsx
 *
 * Delegates to sub-components based on content_type.
 * MOB-B6: 'job_etc_status' and 'conflict_summary' now render real cards.
 */

import React from "react";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";
import { VoiceQuotePreview } from "./VoiceQuotePreview";
import { JobEtcStatusCard } from "./JobEtcStatusCard";
import { ConflictSummaryCard } from "./ConflictSummaryCard";
import type { SnapshotPayload } from "../types-stub";
import type { JobEtcStatusPayload } from "./JobEtcStatusCard";
import type { ConflictSummaryPayload } from "./ConflictSummaryCard";

interface StructuredMessageProps {
  message: {
    id: string;
    structured_content: {
      render_mode: "live" | "snapshot";
      content_type:
        | "quote_preview"
        | "job_etc_status"
        | "conflict_summary"
        | "text";
      entity_id: string | null;
      snapshot_payload: Record<string, unknown> | null;
    };
  };
  onQuoteSubmit?: (quoteId: string) => void;
}

export function StructuredMessage({
  message,
  onQuoteSubmit,
}: StructuredMessageProps) {
  const { render_mode, content_type, entity_id, snapshot_payload } =
    message.structured_content;

  switch (content_type) {
    case "quote_preview":
      return render_mode === "live" ? (
        <VoiceQuotePreview
          mode="live"
          entityId={entity_id ?? undefined}
          onSubmit={onQuoteSubmit}
        />
      ) : (
        <VoiceQuotePreview
          mode="snapshot"
          payload={snapshot_payload as unknown as SnapshotPayload}
          onSubmit={onQuoteSubmit}
        />
      );

    case "job_etc_status":
      return (
        <JobEtcStatusCard
          mode={render_mode}
          entityId={entity_id ?? undefined}
          payload={snapshot_payload as unknown as JobEtcStatusPayload}
          testID="job-etc-status-card"
        />
      );

    case "conflict_summary":
      return (
        <ConflictSummaryCard
          payload={snapshot_payload as unknown as ConflictSummaryPayload}
          testID="conflict-summary-card"
        />
      );

    case "text":
    default:
      // Plain text messages render as VoiceMessageBubble, not StructuredMessage
      return null;
  }
}
