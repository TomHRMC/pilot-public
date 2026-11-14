/**
 * Public Quote — Types
 * Location: apps/web/src/features/public-quote/types.ts
 *
 * All types for the public quote page feature (FE-B14).
 * RULE 1: No auth types imported here — this is an unauthenticated surface.
 */

export interface PublicTenantBranding {
  logoUrl: string | null;
  /** Never null in UI — falls back to '#3B43D6' (Pilot brand-indigo) */
  brandColorHex: string;
}

export interface PublicLineItem {
  description: string;
  quantity: string;
  unitPriceCents: number;
  totalCents: number;
}

export interface PublicQuoteData {
  quoteId: string;
  tenantName: string;
  customerName: string;
  quoteTotalCents: number;
  currency: string;
  lineItems: PublicLineItem[];
  status: "sent" | "accepted" | "declined" | "expired";
  expiresAt: string | null;
  branding: PublicTenantBranding;
  customerAcceptanceComment: string | null;
  customerDeclineComment: string | null;
}

export type DeclineReason =
  | "pricing"
  | "scope"
  | "timing"
  | "other_contractor"
  | "other";

export const DECLINE_REASON_LABELS: Record<DeclineReason, string> = {
  pricing: "Pricing is too high",
  scope: "Scope doesn't fit my needs",
  timing: "Timing doesn't work",
  other_contractor: "Going with another contractor",
  other: "Other reason",
};

export type QuoteActionPhase =
  | "idle"
  | "submitting"
  | "success"
  | "error"
  | "conflict"; // 409

export interface QuoteActionState {
  phase: QuoteActionPhase;
  acceptedAt?: string;
  declinedAt?: string;
  message?: string;
}

export interface QuoteAcceptRequest {
  comment?: string;
}

export interface QuoteDeclineRequest {
  reason: DeclineReason;
  comment?: string;
}

/** Error context returned on 410 for expired links */
export interface ExpiredLinkMeta {
  tenantName?: string;
  tenantPhone?: string;
  tenantEmail?: string;
}
