/**
 * usePreviewBeforeSend — Always-Preview-Before-Send Hook (§16.7)
 *
 * Location: packages/ui/src/hooks/usePreviewBeforeSend.ts
 * Exported from: packages/ui/src/index.ts under // ── FE-B6 Exports ──
 *
 * Established in FE-B6 (customer comms outbound).
 * Consumed by FE-B10 (SMS inbound free-form reply).
 *
 * Pattern ref: mvp-arch.md §16.7; pilot-react-engineer-methods.md §9.6
 *
 * ⚠️ INTERFACE LOCKED — changes require FE-B10 impact review.
 *
 * Architecture rules enforced here:
 * 1. ALWAYS-PREVIEW-BEFORE-SEND: send() throws if called without prior preview()
 * 2. ONLINE-ONLY: send path disabled when navigator.onLine === false
 * 3. SERVER-SIDE RENDER: template mode always calls POST /preview; free-form synthesizes locally
 * 4. PREVIEW TOKEN: UUID generated at preview-call time, cleared after send/cancel/close
 */

import React, { useCallback, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
// Static import is safe here — message-preview/ does not import from hooks/
import { MessagePreviewModal as MessagePreviewModalComponent } from "../message-preview/web/MessagePreviewModal";
import type {
  CommunicationPreviewRequest,
  CommunicationPreviewResponse,
  CommunicationSendRequest,
  CommunicationSendResponse,
  FreeFormPreviewData,
  FreeFormSendResponse,
  MessagePreviewModalOverrideProps,
  PreviewInput,
  UsePreviewBeforeSendOptions,
  UsePreviewBeforeSendReturn,
} from "../message-preview/types";

// ── Internal constants ────────────────────────────────────────────────────────

const PREVIEW_ENDPOINT = "/api/v1/communications/preview";
const SEND_ENDPOINT = "/api/v1/communications/send";
/** Polling interval for delivery status when status === "pending" */
const POLLING_INTERVAL_MS = 2000;
/** Polling timeout — show "delivery unknown" after this */
const POLLING_TIMEOUT_MS = 30_000;

// ── Helpers ───────────────────────────────────────────────────────────────────

function generatePreviewToken(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return `preview-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function computeSmsSegments(body: string): number {
  // GSM-7: 160 chars/segment; Unicode: 70 chars/segment
  // Simple ASCII heuristic — covers the vast majority of technician messages
  // eslint-disable-next-line no-control-regex
  const isAscii = /^[\u0000-\u007F]*$/.test(body);
  const charsPerSegment = isAscii ? 160 : 70;
  return Math.ceil(body.length / charsPerSegment) || 1;
}

async function callPreviewApi(
  req: CommunicationPreviewRequest,
): Promise<CommunicationPreviewResponse> {
  const res = await fetch(PREVIEW_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      `Preview failed: ${res.status} ${detail.detail ?? res.statusText}`,
    );
  }
  return res.json() as Promise<CommunicationPreviewResponse>;
}

async function callSendApi(
  req: CommunicationSendRequest,
): Promise<CommunicationSendResponse> {
  const res = await fetch(SEND_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string };
    // MSW enforcement contract (test-only: 403 + preview_not_called)
    if (res.status === 403 && detail.detail === "preview_not_called") {
      throw new Error(
        "[usePreviewBeforeSend] send() called before preview() — this is a bug",
      );
    }
    // Quota exhaustion
    if (
      res.status === 429 ||
      (typeof detail.detail === "string" && detail.detail.includes("quota"))
    ) {
      throw new Error("QUOTA_EXHAUSTED");
    }
    throw new Error(
      `Send failed: ${res.status} ${detail.detail ?? res.statusText}`,
    );
  }
  return res.json() as Promise<CommunicationSendResponse>;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * usePreviewBeforeSend — always-preview-before-send (§16.7) hook.
 *
 * Establishes in FE-B6. Consumed by FE-B10 (free-form SMS reply composer).
 * The hook enforces that send() cannot be called without a prior preview().
 *
 * @example Template-based (FE-B6)
 * const { preview, MessagePreviewModal } = usePreviewBeforeSend();
 * <Button onPress={() => preview({ mode: 'template', customerId, templateCode: 'on_my_way', variables: { eta_minutes: 20 } })} />
 * <MessagePreviewModal />
 *
 * @example Free-form (FE-B10)
 * const { preview, MessagePreviewModal } = usePreviewBeforeSend();
 * <Button onPress={() => preview({ mode: 'free-form', customerId, freeFormBody: text, threadId })} />
 * <MessagePreviewModal />
 */
export function usePreviewBeforeSend(
  options?: UsePreviewBeforeSendOptions,
): UsePreviewBeforeSendReturn {
  // ── State ─────────────────────────────────────────────────────────────────
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [previewData, setPreviewData] = useState<
    CommunicationPreviewResponse | FreeFormPreviewData | null
  >(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sendResult, setSendResult] = useState<
    CommunicationSendResponse | FreeFormSendResponse | null
  >(null);
  const [sendError, setSendError] = useState<Error | null>(null);

  // ── Internal refs (not reactive — hook contract enforcement) ───────────────
  /** Enforcement token: must be non-null to call send() */
  const previewToken = useRef<string | null>(null);
  /** The original preview input, retained for retry after send failure */
  const pendingInput = useRef<PreviewInput | null>(null);
  /** communication_id for delivery polling */
  const pollingCommunicationId = useRef<string | null>(null);
  /** Polling start timestamp for 30s timeout */
  const pollingStartedAt = useRef<number | null>(null);

  // ── Delivery status polling ────────────────────────────────────────────────
  // Derives customerId from pendingInput ref for the query key
  const pollingCustomerId =
    pendingInput.current != null ? pendingInput.current.customerId : null;
  const pollingCommId = pollingCommunicationId.current;

  useQuery<{ communication_id: string; status: string } | null>({
    queryKey: ["comm-delivery-status", pollingCommId, pollingCustomerId],
    enabled: pollingCommId !== null && pollingCustomerId !== null,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when resolved or timed out
      if (data && data.status !== "pending") return false;
      const elapsed = pollingStartedAt.current
        ? Date.now() - pollingStartedAt.current
        : 0;
      if (elapsed >= POLLING_TIMEOUT_MS) return false;
      return POLLING_INTERVAL_MS;
    },
    queryFn: async () => {
      const res = await fetch(
        `/api/v1/customers/${pollingCustomerId}/communications?page=1&page_size=50`,
      );
      if (!res.ok) throw new Error("Polling failed");
      const data = (await res.json()) as {
        items: Array<{ communication_id: string; status: string }>;
      };
      return (
        data.items.find((i) => i.communication_id === pollingCommId) ?? null
      );
    },
    gcTime: 0,
  });

  // ── preview() ─────────────────────────────────────────────────────────────
  const preview = useCallback(async (input: PreviewInput): Promise<void> => {
    // Online check (§G3: no offline path for customer comms)
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      throw new Error("OFFLINE");
    }

    setSendError(null);
    setSendResult(null);
    setIsPreviewLoading(true);

    try {
      if (input.mode === "template") {
        const req: CommunicationPreviewRequest = {
          customer_id: input.customerId,
          template_code: input.templateCode,
          variables: input.variables ?? {},
          channel_override: input.channelOverride ?? null,
        };
        const data = await callPreviewApi(req);
        previewToken.current = generatePreviewToken();
        pendingInput.current = input;
        setPreviewData(data);
      } else {
        // free-form: synthesize locally (FE-B10 path; no server render)
        const freeFormData: FreeFormPreviewData = {
          rendered_subject: null,
          rendered_body: input.freeFormBody,
          recipient_name: "",
          recipient_address: "",
          actual_channel: input.channelOverride ?? "sms",
          editable_variables: [],
        };
        previewToken.current = generatePreviewToken();
        pendingInput.current = input;
        setPreviewData(freeFormData);
      }
      setIsModalOpen(true);
    } finally {
      setIsPreviewLoading(false);
    }
  }, []);

  // ── send() ────────────────────────────────────────────────────────────────
  const send = useCallback(async (): Promise<
    CommunicationSendResponse | FreeFormSendResponse
  > => {
    // Enforcement contract (§F3)
    if (previewToken.current === null) {
      throw new Error(
        "[usePreviewBeforeSend] send() called before preview() — this is a bug",
      );
    }

    // Online check
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      throw new Error("OFFLINE");
    }

    if (!pendingInput.current) {
      throw new Error(
        "[usePreviewBeforeSend] no pending input — this is a bug",
      );
    }

    setIsSending(true);
    setSendError(null);

    try {
      let result: CommunicationSendResponse | FreeFormSendResponse;

      if (pendingInput.current.mode === "template") {
        const input = pendingInput.current;
        const req: CommunicationSendRequest = {
          customer_id: input.customerId,
          template_code: input.templateCode,
          job_id: input.jobId ?? null,
          variables: input.variables ?? {},
          channel_override: input.channelOverride ?? null,
        };
        result = await callSendApi(req);
      } else {
        // free-form send (FE-B10)
        const input = pendingInput.current;
        const res = await fetch("/api/v1/communications/send-free-form", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            customer_id: input.customerId,
            body: input.freeFormBody,
            thread_id: input.threadId,
            channel_override: input.channelOverride ?? null,
          }),
        });
        if (!res.ok) {
          const detail = (await res.json().catch(() => ({}))) as {
            detail?: string;
          };
          throw new Error(
            `Free-form send failed: ${res.status} ${detail.detail ?? res.statusText}`,
          );
        }
        result = (await res.json()) as FreeFormSendResponse;
      }

      // Start delivery polling when status is pending (§G8)
      if ("status" in result && result.status === "pending") {
        pollingCommunicationId.current = result.communication_id;
        pollingStartedAt.current = Date.now();
      }

      // Reset token after successful send
      previewToken.current = null;
      setSendResult(result);
      setIsModalOpen(false);
      options?.onSendSuccess?.(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setSendError(error);
      // Retain previewToken on failure so retry is possible (§G8)
      options?.onSendError?.(error);
      throw error;
    } finally {
      setIsSending(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options?.onSendSuccess, options?.onSendError]);

  // ── closeModal() ──────────────────────────────────────────────────────────
  const closeModal = useCallback(() => {
    previewToken.current = null;
    setIsModalOpen(false);
    setPreviewData(null);
    setSendError(null);
  }, []);

  // ── Embedded MessagePreviewModal ──────────────────────────────────────────
  // Wrapped in a stable component reference so consumers can place it in JSX
  // without causing infinite re-renders. The inner component reads current state
  // from closure — React will re-render when parent (hook owner) state changes.
  const smsSegmentCount =
    previewData?.actual_channel === "sms"
      ? computeSmsSegments(previewData.rendered_body)
      : undefined;

  // We declare the embedded modal as a stable function component using useCallback
  // so that it maintains identity across renders.
  const EmbeddedModalComponent = useCallback(
    function BoundMessagePreviewModal(
      overrides: Partial<MessagePreviewModalOverrideProps>,
    ) {
      return React.createElement(MessagePreviewModalComponent, {
        previewData,
        isOpen: isModalOpen,
        onConfirm: () => send().catch(() => {}),
        onCancel: closeModal,
        isSending,
        smsSegmentCount,
        ...overrides,
      });
    },
    [previewData, isModalOpen, send, closeModal, isSending, smsSegmentCount],
  );

  return {
    preview,
    send,
    isPreviewLoading,
    isSending,
    previewData,
    isModalOpen,
    closeModal,
    MessagePreviewModal: EmbeddedModalComponent,
    sendResult,
    sendError,
  };
}

// Re-export types for downstream consumers
export type {
  UsePreviewBeforeSendOptions,
  UsePreviewBeforeSendReturn,
  PreviewInput,
} from "../message-preview/types";
