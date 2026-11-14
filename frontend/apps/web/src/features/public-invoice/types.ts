/**
 * Public Invoice — Types
 * Location: apps/web/src/features/public-invoice/types.ts
 *
 * RULE 1: No auth types imported — unauthenticated surface.
 * RULE 6: PaymentIntent created with ACTUAL chosen amount (not full invoice amount).
 */

import type {
  PublicLineItem,
  PublicTenantBranding,
} from "../public-quote/types";
export type { PublicLineItem, PublicTenantBranding };

export interface PublicInvoiceData {
  invoiceId: string;
  tenantName: string;
  customerName: string;
  invoiceTotalCents: number;
  amountPaidCents: number;
  amountDueCents: number;
  currency: string;
  lineItems: PublicLineItem[];
  status: "unpaid" | "partial" | "paid";
  dueDate: string | null;
  branding: PublicTenantBranding;
  /** Whether the tenant can accept card payments (Stripe Connect charges enabled). Defaults false when absent so a stale backend fails closed to the manual panel. */
  cardPaymentsEnabled: boolean;
  /** Backend reason when card payments are unavailable; the frontend is reason-agnostic (gates on cardPaymentsEnabled only). */
  paymentUnavailableReason: "not_connected" | "charges_disabled" | null;
  /** Tenant billing-contact phone shown on the manual-payment panel (null = not entered). */
  tenantPhone: string | null;
  /** Tenant billing-contact email shown on the manual-payment panel (null = not entered). */
  tenantEmail: string | null;
}

/** State machine for the invoice payment modal (design doc Section D.1) */
export type PaymentModalState =
  | {
      phase: "amount-select";
      selectedAmountCents: number;
      comment: string;
      adjusting: boolean;
    }
  | { phase: "pi-loading" }
  | {
      phase: "card-entry";
      clientSecret: string;
      paymentIntentId: string;
      selectedAmountCents: number;
    }
  | { phase: "submitting" }
  | { phase: "processing"; paymentIntentId: string }
  | { phase: "success"; amountPaidCents: number }
  | { phase: "error"; error: string; recoverable: true };

/** Internal state for the amount selector (design doc Section D.2) */
export interface AmountSelectorState {
  adjusting: boolean;
  customAmountCents: number;
  comment: string;
  commentError: string | null;
  amountError: string | null;
}

export interface PaymentIntentRequest {
  amount_cents: number;
  comment?: string;
}

export interface PaymentIntentResponse {
  client_secret: string;
  payment_intent_id: string;
}

/** Compute variance display values (design doc Section D.2) */
export function derivePaymentVariance(
  selectedCents: number,
  invoiceTotalCents: number,
): {
  varianceCents: number;
  remainingCents: number;
  isOverpayment: boolean;
} {
  const varianceCents = selectedCents - invoiceTotalCents;
  return {
    varianceCents,
    remainingCents: Math.max(invoiceTotalCents - selectedCents, 0),
    isOverpayment: varianceCents > 0,
  };
}

/** Normalize snake_case API response to camelCase invoice data */
export function normalizeInvoiceData(
  raw: Record<string, unknown>,
): PublicInvoiceData {
  const branding = raw.branding as {
    logo_url: string | null;
    brand_color_hex: string | null;
  };
  const lineItems = (raw.line_items as Array<Record<string, unknown>>).map(
    (item) => ({
      description: item.description as string,
      quantity: item.quantity as string,
      unitPriceCents: item.unit_price_cents as number,
      totalCents: item.total_cents as number,
    }),
  );

  return {
    invoiceId: raw.invoice_id as string,
    tenantName: raw.tenant_name as string,
    customerName: raw.customer_name as string,
    invoiceTotalCents: raw.invoice_total_cents as number,
    amountPaidCents: raw.amount_paid_cents as number,
    amountDueCents: raw.amount_due_cents as number,
    currency: (raw.currency as string) ?? "USD",
    lineItems,
    status: raw.status as PublicInvoiceData["status"],
    dueDate: (raw.due_date as string | null) ?? null,
    branding: {
      logoUrl: branding.logo_url,
      // eslint-disable-next-line pilot/no-hardcoded-design-values
      brandColorHex: branding.brand_color_hex ?? "#3B43D6",
    },
    // STRIPE-CONNECT-1-C: card-payment capability + manual-payment contact fields.
    // Defaults false when absent so a stale backend fails closed to the manual panel,
    // never to a broken Pay button.
    cardPaymentsEnabled: (raw.card_payments_enabled as boolean) ?? false,
    paymentUnavailableReason:
      (raw.payment_unavailable_reason as PublicInvoiceData["paymentUnavailableReason"]) ??
      null,
    tenantPhone: (raw.tenant_phone as string | null) ?? null,
    tenantEmail: (raw.tenant_email as string | null) ?? null,
  };
}
