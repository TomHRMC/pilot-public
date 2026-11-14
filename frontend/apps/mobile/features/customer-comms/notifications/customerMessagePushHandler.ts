/**
 * customerMessagePushHandler — Expo Notifications handler for customer_message push
 *
 * Location: apps/mobile/features/customer-comms/notifications/customerMessagePushHandler.ts
 *
 * Handles push notification taps for inbound customer SMS messages.
 * Navigates to /(tabs)/(home)/inbox/[threadId] on tap.
 * Invalidates thread list query to ensure unread counts are fresh.
 *
 * Deep-link URL: pilot:///(tabs)/(home)/inbox/[threadId]
 *
 * Design doc Decision 1, Section A.3.1
 */

import type { QueryClient } from "@tanstack/react-query";

interface CustomerMessagePushPayload {
  type: "customer_message";
  thread_id: string;
  customer_id?: string;
  customer_name?: string;
  message_preview?: string;
  unread_count?: number;
}

type RouterPushFn = (href: string) => void;

/**
 * handleCustomerMessagePush — called when user taps a customer_message push
 *
 * @param payload — push notification data payload
 * @param push — router.push function (passed from app root)
 * @param queryClient — TanStack Query client for cache invalidation
 */
export function handleCustomerMessagePush(
  payload: CustomerMessagePushPayload,
  push: RouterPushFn,
  queryClient: QueryClient,
): void {
  if (payload.type !== "customer_message") return;
  if (!payload.thread_id) return;

  // Invalidate thread list so unread count reflects the new message
  void queryClient.invalidateQueries({ queryKey: ["customer-threads"] });

  // Also prefetch thread messages if possible
  void queryClient.invalidateQueries({
    queryKey: ["thread-messages", payload.thread_id],
  });

  // Navigate to the thread screen (Expo Router)
  push(`/(tabs)/(home)/inbox/${payload.thread_id}`);
}

/**
 * isCustomerMessagePayload — type guard for the push payload
 */
export function isCustomerMessagePayload(
  data: unknown,
): data is CustomerMessagePushPayload {
  if (!data || typeof data !== "object") return false;
  const d = data as Record<string, unknown>;
  return d.type === "customer_message" && typeof d.thread_id === "string";
}
