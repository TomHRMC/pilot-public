/**
 * Messaging Setup Page — C-B9
 *
 * Route: /settings/messaging
 *
 * Thin server component (RULE 9) — no "use client", no data fetching.
 * Renders MessagingSetupClient which owns all logic.
 *
 * Design spec: batch-c-b9-ui-design-spec.md §4.1
 */
import { MessagingSetupClient } from "@/components/settings/messaging/MessagingSetupClient";

export const metadata = {
  title: "Messaging Setup — Pilot",
};

export default function MessagingSetupPage() {
  return <MessagingSetupClient />;
}
