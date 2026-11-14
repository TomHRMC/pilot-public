/**
 * InvoiceSignoff — WatermelonDB model for offline invoice sign-off capture
 *
 * Location: apps/mobile/database/models/InvoiceSignoff.ts
 *
 * Mirrors the backend `invoice_signoff` table for offline-first signature capture.
 * The base64 PNG travels inline in the mutation payload (design §G-R5) — no
 * presigned-PUT round-trip. The sync engine pushes to
 * POST /api/v1/invoices/{invoice_id}/signoff with Idempotency-Key header.
 *
 * Per batch-ce-1-design.md §F.2 and §E (§15 Offline Ops Contract).
 */

import { field } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class InvoiceSignoff extends SyncableModel {
  static table = "invoice_signoffs";

  /** UUID of the invoice this sign-off belongs to */
  @field("invoice_id") declare invoiceId: string;

  /** Customer's printed name as entered by the tech */
  @field("signed_by_name") declare signedByName: string;

  /** Whether the customer acknowledged the terms (always true — CHECK constraint) */
  @field("terms_acknowledged") declare termsAcknowledged: boolean;

  /** Base64-encoded PNG signature image (~20–60KB, inline in payload) */
  @field("signature_png_base64") declare signaturePngBase64: string;

  /** User ID of the tech who captured the signature */
  @field("captured_by") declare capturedBy: string;
}
