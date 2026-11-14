/**
 * UnroutedMessageRow — Single row in the unrouted queue
 *
 * Location: apps/web/src/features/sms-unrouted/components/UnroutedMessageRow.tsx
 *
 * Shows: received timestamp, masked phone, first 80 chars of body, Assign CTA.
 *
 * Design doc Section A.2.3
 */

"use client";

import React from "react";
import Link from "next/link";
import type { UnroutedMessage } from "@pilot/ui";

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface UnroutedMessageRowProps {
  message: UnroutedMessage;
  testID?: string;
}

export function UnroutedMessageRow({
  message,
  testID,
}: UnroutedMessageRowProps) {
  const bodyPreview =
    message.body.length > 80 ? `${message.body.slice(0, 80)}…` : message.body;

  return (
    <tr
      className="hover:bg-neutral-50 transition-colors"
      data-testid={testID ?? `unrouted-row-${message.unrouted_id}`}
    >
      <td className="px-4 py-3 text-caption text-neutral-600 whitespace-nowrap">
        {formatDate(message.received_at)}
      </td>
      <td className="px-4 py-3 text-body text-neutral-900 font-medium">
        {message.from_number}
      </td>
      <td className="px-4 py-3 text-body text-neutral-600 max-w-md truncate">
        {bodyPreview}
      </td>
      <td className="px-4 py-3 text-right">
        <Link
          href={`/settings/integrations/sms/unrouted/${message.unrouted_id}`}
          className="inline-flex items-center px-3 py-1.5 rounded-md text-caption font-medium bg-brand-600 text-white hover:bg-brand-800 transition-colors"
          data-testid={`assign-btn-${message.unrouted_id}`}
        >
          Assign
        </Link>
      </td>
    </tr>
  );
}
