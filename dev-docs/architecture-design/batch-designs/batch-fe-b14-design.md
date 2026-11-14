# FE-B14 Batch Design — Customer-Facing Public Surfaces & Email Templates (Pass 4 Tier 4 #13)

**Status**: Ready for Implementation
**Date**: 2026-05-27
**Author**: Pilot Architect
**Prerequisite Batches**: FE-B0 through FE-B13 complete
**Backend Gate**: BE-B15 (A80–A83: signed URL infrastructure, Stripe one-time payment, email template pipeline, entity-bound customer comments)
**Gates Downstream**: None (FE-B14 is terminal in the frontend batch graph)
**Test Subfolder**: `apps/web/__tests__/batch_fe_b14/`

---

## Prerequisite Reads Completed

| Source | Key facts extracted |
|:---|:---|
| `frontend-pass-4-tier-4-flow-13-customer-facing-public-link-styling-spec.md` | 12 locked decisions: public quote/invoice layouts (ASCII specs), accept/decline overlays with comment (2000-char limit), invoice payment modal with amount adjustment checkbox, expired-link page, 16-template email framework with customer-facing vs internal split, email branding settings sub-surface at Settings > Communications, state-aware revisit table, entity-bound comment storage schema, SMS short-link (pilot.tr) as optional MVP fallback |
| `pilot-app-mvp-frontend-impl-plan.md §6 FE-B14` | 8-item execution order (public quote → public invoice → Stripe one-time + variance → state-aware revisit → customer comments → email branding settings → 16 template implementations → EmailBrandingPreview flush); targets: 50+ unit, 14+ integration, 3+ E2E |
| `mvp-arch.md §18` | §18.2 HMAC token verification: 410 GONE on expired/revoked, 401 UNAUTHORIZED on tampered; §18.5 payment flow: frontend calls `/payment-intent` → gets `client_secret` → Stripe Elements confirms → `/confirm-payment` advisory → webhook finalizes; §18.6 state-aware revisit table; §18.7 entity-bound comment column additions; §18.8 template rendering pipeline (server-side via `email_template_renderer.py`) |
| `packages/ui/src/stripe-payment/StripePaymentForm.tsx` | **LOCKED interface confirmed**: `stripePublishableKey`, `clientSecret`, `mode: 'subscription' \| 'one-time'`, `paymentAmountCents?`, `submitLabel?`, `onSuccess(StripePaymentResult)`, `onError?(StripePaymentError)`, `onLoadingChange?`, `disabled?`, `testID?`. One-time mode already calls `stripe.confirmPayment()`; shows amount display in neutral card. `return_url` for `one-time` hardcoded to `/payment/success` — FE-B14 overrides via `submitLabel` and wraps externally for redirect control. No structural changes to this file. |
| `packages/ui/src/email-branding-preview/EmailBrandingPreview.tsx` | **FE-B1 skeleton confirmed**: props `branding: TenantBranding \| null`, `previewWidth?: number`, `className?: string`. The fleshed FE-B14 version must add `templateKey?: EmailTemplateId`, `previewHtml?: string`, `isLoading?: boolean` — backward-compatible (all additive optional). Skeleton renders shimmer when `branding === null`; placeholder text otherwise. FE-B14 replaces placeholder with iframe rendering `previewHtml`. |
| `packages/ui/src/setting-control/SettingControl.tsx` | `saveMode='blur'` triggers `onSave(draftValue)` on blur; `isSaved` state shows "✓ Saved" badge for 2 seconds. Email branding fields (signature, footer text) use `inputType='string'` with `saveMode='blur'`. Logo upload and color picker are explicit-save fields (separate upload pattern). LOCKED — no modifications. |
| `backend/api/routes/public_quotes.py` | `GET /api/v1/public/quotes/{signed_token}` → `PublicQuoteResponse` (includes `status: 'sent' \| 'accepted' \| 'declined' \| 'expired'`, `branding.logo_url`, `branding.brand_color_hex`, `customer_acceptance_comment`, `customer_decline_comment`). `POST .../accept` body: `{comment?}`. `POST .../decline` body: `{reason, comment?}`. 409 CONFLICT on double-accept/decline. |
| `backend/api/routes/public_invoices.py` | `GET /api/v1/public/invoices/{signed_token}` → `PublicInvoiceResponse` (includes `amount_due_cents`, `amount_paid_cents`, `status: 'unpaid' \| 'partial' \| 'paid'`). `POST .../payment-intent` body: `{amount_cents, comment?}` — backend validates comment required when `amount_cents != invoice_total_cents` (422). Returns `{client_secret, payment_intent_id}`. `POST .../confirm-payment` → `{status: 'pending_confirmation'}` advisory only; final payment record via webhook. |
| `backend/api/routes/tenant_email_branding.py` | `GET /api/v1/settings/email-branding` (settings.view), `PATCH /api/v1/settings/email-branding` (settings.manage), `POST .../logo-upload-url` → `{upload_url, s3_path}` (settings.manage), `POST .../preview` body: `{template_id}` → `{subject, body_html, body_plain}`, `POST .../test-send` → sends welcome template to requesting user's email. All 5 endpoints confirmed. |
| `frontend/packages/ui/src/index.ts` | `EmailBrandingPreview` and `TenantBranding` already exported from `./email-branding-preview` (FE-B1 block). `StripePaymentForm` and types exported from `./stripe-payment` (FE-B13 block). FE-B14 must update this barrel with the fleshed `EmailBrandingPreviewProps` new fields and new FE-B14 type exports. |
| `frontend/apps/web/src/app/(authed)/settings/` | Confirmed sub-directories: `integrations/`, `my-account/`, `notifications/`, `operations/`, `sync-storage/`, `voice-ai/`. **`communications/` does NOT exist yet** — FE-B14 creates this new top-level settings group. |

---

## Resolved Design Decisions

### Decision 1 — `StripePaymentForm` One-Time-Payment Mode Extension

**Decision**: The `StripePaymentForm` component at `packages/ui/src/stripe-payment/StripePaymentForm.tsx` is **NOT modified** for the one-time-payment invoice flow. The component already supports `mode='one-time'` and `paymentAmountCents` (locked interface, FE-B13). The amount variance UI belongs to a new `InvoicePaymentModal` feature component in `apps/web/src/features/public-invoice/`, not inside `StripePaymentForm`.

**Why this split**: the Stripe payment flow for invoice payment requires a two-step sequence:
1. Customer selects amount (full or adjusted) → FE calls `POST /payment-intent` → receives `client_secret`
2. `client_secret` is passed to `<StripePaymentForm mode="one-time" clientSecret={clientSecret} paymentAmountCents={selectedAmountCents}>` for card entry

The amount selection state machine lives *outside* Stripe Elements. `StripePaymentForm` only owns the Stripe Elements boundary. This preserves RULE 1 (single Elements boundary) and keeps `StripePaymentForm` unmodified.

**Additive extension to `types.ts`** (the only file that changes): FE-B14 adds three optional props to `StripePaymentFormProps` for invoice-context annotations:

```typescript
// ADDITIVE ONLY — does not change existing subscription-mode behavior
invoiceToken?: string;          // for return_url construction on redirect flows
onPaymentSuccess?: (result: StripePaymentResult & { actualAmountPaidCents: number }) => void;
```

> **LOCKED**: `invoiceToken?` and `onPaymentSuccess?` are the only additions. `onSuccess` callback for subscription mode is unchanged. FE-B13 usage (`mode='subscription'`) is unaffected — neither prop is used in subscription mode.

**PaymentElement vs CardElement**: Both modes use `PaymentElement` (unified — already confirmed in the implementation). No change.

**FE-B13 regression**: zero risk. The two new props are optional with no default behavior. Existing usages omit them and behavior is identical.

---

### Decision 2 — Public Quote/Invoice Route Structure (Unauthenticated)

**Decision**: Public pages live **outside** `(authed)` at the app root level:

```
apps/web/src/app/
├── q/
│   └── [token]/
│       └── page.tsx          # GET /api/v1/public/quotes/{token} — unauthenticated
├── i/
│   └── [token]/
│       └── page.tsx          # GET /api/v1/public/invoices/{token} — unauthenticated
├── link-expired/
│   └── page.tsx              # Shared expired/revoked link landing (no token context)
├── (authed)/                 # All authenticated routes (unchanged)
└── login/                    # Already outside authed
```

**Route paths confirmed**: `/q/{signed-token}` for quotes, `/i/{signed-token}` for invoices. These match the backend paths `GET /api/v1/public/quotes/{signed_token}` and `GET /api/v1/public/invoices/{signed_token}`. The frontend token segment maps directly to the signed token passed to the API — no additional expansion layer needed in the frontend.

**`generateMetadata`**: Both page files implement `generateMetadata` for SEO and link preview quality:
```typescript
// apps/web/src/app/q/[token]/page.tsx
export async function generateMetadata({ params }): Promise<Metadata> {
  // Fetch quote data; on failure return generic metadata
  return {
    title: `Quote QU-XXXX from ${tenantName}`,
    description: `View and accept or decline your quote from ${tenantName}`,
    robots: 'noindex, nofollow',   // customer-specific; don't index
  };
}
```

**Expired vs invalid token**:
- HTTP **410 GONE** (expired or revoked): renders the specific "This link has expired" page with tenant contact info (decision spec §6). This state is surfaced with `fault-50` background and `fault-700` text.
- HTTP **401 UNAUTHORIZED** (cryptographically invalid/tampered token): renders a generic "Invalid link" error — no tenant contact info, because the tenant cannot be identified from a tampered token.
- The two cases are handled via distinct error page branches in the data-fetching layer.

**`useAuth()` rule**: Neither `/q/[token]` nor `/i/[token]` may import or call `useAuth()`. These are fully unauthenticated. Any attempt to read auth context in these files is a hard implementation error.

---

### Decision 3 — Amount Variance UI Flow

**Decision**: The payment modal uses a single amount input, not a three-option radio group. The spec ASCII (§5) shows a pre-filled amount field with an "Adjust amount" checkbox, which is the correct pattern:

**Default state**: amount input pre-filled with `invoice.amount_due_cents`, checkbox "Adjust amount (pay more or less)" unchecked. Customer sees "Pay $X,XXX.XX" and card entry — the fastest path for full payment.

**Adjusted state** (checkbox ticked): the amount input becomes editable. The customer modifies the value. A comment textarea appears below (required — cannot submit without comment text when amount differs from `amount_due_cents`).

**Variance display**: when adjusted amount is entered, a live computed row appears:
```
Variance: -$385.83 (10% less than invoice total)
Remaining balance after this payment: $385.83
```

**Minimum constraint**: `amount_cents` must be `> 0`. No other minimum (partial payments of any positive amount are permitted). The backend enforces this; the frontend pre-validates.

**Payment Intent lifecycle**: the customer selects an amount → clicks "Continue to payment" → the `InvoicePaymentModal` calls `POST /payment-intent` with `{amount_cents, comment?}` → receives `client_secret` → renders `<StripePaymentForm>` with the client_secret + selected amount. The Payment Intent is created for the *customer-selected* amount — Stripe processes exactly that amount. No re-initialization after amount selection.

**Partial payment copy**: "The remaining balance of $X will stay on your invoice. [Tenant name] can collect the remainder later." This appears below the variance row.

**State machine** (fully specified in Section D):
`amount-select` → `payment-intent-loading` → `card-entry` → `submitting` → `processing` (advisory) → `success` | `error`

---

### Decision 4 — `EmailBrandingPreview` Fleshing from FE-B1 Skeleton

**Decision**: The preview renders an **iframe** containing the server-fetched `body_html` from `POST /api/v1/settings/email-branding/preview`. This is the only approach that guarantees pixel-accurate rendering of the server-side Jinja2/HTML templates without re-implementing the entire template engine in React.

**Rendering flow**:
1. `EmailBrandingSettingsPanel` holds the current branding form state in local React state
2. Each field update (via `SettingControl` `onSave` blur) triggers debounced re-fetch of preview HTML
3. The fetched `body_html` is passed as `previewHtml` prop to `EmailBrandingPreview`
4. `EmailBrandingPreview` renders the HTML in a sandboxed iframe: `<iframe sandbox="allow-same-origin" srcDoc={previewHtml} />`

**Update timing**: preview updates *after* each field save (blur-saved field → `SettingControl.onSave` fires → panel re-fetches preview). Not real-time during typing — saves on blur trigger the re-fetch. This is consistent with `saveMode='blur'` from FE-B11.

**Template selector**: a `<select>` dropdown above the preview pane lets the owner switch which template is being previewed. Options are the 6 customer-facing templates (those that render with tenant branding). This is passed as `templateKey` prop to `EmailBrandingPreview`. Default: `quote_sent`.

**Preview is web-only**: email branding settings are owner-task, web-only. No mobile preview.

**New fleshed `EmailBrandingPreviewProps`** (additive, backward-compatible):
```typescript
export interface EmailBrandingPreviewProps {
  branding: TenantBranding | null;          // FE-B1 (unchanged)
  previewWidth?: number;                     // FE-B1 (unchanged)
  className?: string;                        // FE-B1 (unchanged)
  templateKey?: EmailTemplateId;             // FE-B14 NEW — which template to show
  previewHtml?: string;                      // FE-B14 NEW — server-rendered HTML blob
  isLoading?: boolean;                       // FE-B14 NEW — shows skeleton during re-fetch
}
```

---

### Decision 5 — Customer Comments: Submission and Display

**Decision**: Comment field visibility and behavior per entity type:

**Quote public page**: comment textarea appears *inside the confirmation overlay* triggered by clicking Accept or Decline — not always visible on the quote page itself. Customer must explicitly initiate the action before seeing the comment field. This prevents the page looking like a form.

**Invoice public page**: comment textarea appears conditionally when "Adjust amount" checkbox is ticked. For the full-amount payment path, no comment textarea appears (no variance = no comment needed). Comment is required by both frontend validation and the backend (`422` if `amount_cents != invoice_total_cents` and `comment` is absent).

**Character limit**: 2,000 characters for all comment types (accept, decline, payment variance). Spec §2 confirms. Live character counter displayed below textarea: `{count} / 2000`.

**Post-submission display**: after accept/decline, the public page transitions to a success confirmation that repeats the comment back: "Your comment: '{text}'". This provides confirmation to the customer that the comment was received. On revisit (state-aware), the same comment is surfaced.

**Tenant-side display**: customer comments surface in two places in the tenant's Pilot view:
- **Quote detail page** (`/quotes/{id}`): a prominently-styled card block at the top of the acceptance/decline section when present — not in the activity feed.
- **Invoice detail page** (`/invoices/{id}/payments/{id}`): on the payment record, variance + comment displayed together.
- NOT in the notification bell or activity feed (entity-bound per arch §18.7).

---

### Decision 6 — Email Templates: Visual Review Workflow

**Decision**: The 16 templates are reviewed via a dedicated settings sub-surface at `/settings/communications/email-templates` (owner-only). This is a tenant-facing settings page, not an internal QA tool.

**Surface layout**: a two-pane layout:
- Left pane: list of all 16 templates grouped by category (customer-facing / internal). Each row shows template name, trigger event, audience (customer vs tenant user).
- Right pane: preview iframe rendered by calling `POST /api/v1/settings/email-branding/preview` with the selected `template_id`.

Tenant owners can click any template to preview it with their current branding applied. For internal templates (Pilot standard branding), the preview renders with Pilot branding regardless of tenant customization.

**The 16 templates** (locked from spec §7, Table 1):

| ID | Display Name | Category | Trigger |
|:---|:---|:---|:---|
| `welcome` | Welcome / signup confirmation | internal | Tenant signup complete |
| `email_verification` | Email verification code | internal | Email verify request |
| `quote_sent` | Quote sent | customer_facing | Tenant sends quote |
| `quote_accepted` | Quote accepted | internal | Customer accepts |
| `quote_declined` | Quote declined | internal | Customer declines |
| `quote_expiring_soon` | Quote expiring soon | customer_facing | 3 days before expiry |
| `invoice_sent` | Invoice sent | customer_facing | Tenant sends invoice |
| `payment_received_tenant` | Payment received (your copy) | internal | Stripe payment success |
| `payment_received_customer` | Payment received (receipt) | customer_facing | Stripe payment success |
| `payment_failed` | Payment failed | customer_facing | Stripe payment failure |
| `subscription_renewal_receipt` | Subscription renewal receipt | internal | Stripe subscription renews |
| `subscription_payment_failed` | Subscription payment failed | internal | Stripe subscription fails |
| `trial_expiring_soon` | Trial expiring soon | internal | 7/3/1 days before trial end |
| `trial_expired` | Trial expired | internal | Trial end date reached |
| `password_reset` | Password reset | internal | Password reset request |
| `mfa_reset_by_owner` | MFA reset by owner | internal | Owner resets user MFA |
| `data_export_ready` | Data export ready | internal | Data export completion |

> Note: `payment_received` is split into two rows: the tenant copy and the customer receipt copy, reflecting the two distinct rendering contexts from spec §7.

**Copy authoring**: placeholder variables (`{{tenant_name}}`, `{{quote_link}}`, `{{quote_total}}`, etc.) are used for development. Tom authors final copy as pre-launch hygiene. FE-B14 does not block on final copy — placeholder values make templates visually reviewable.

**FE-B14 scope for templates**: visual review only. Backend (BE-B15/A82) renders the templates. FE-B14 wires the preview surface and validates visual correctness against the spec's structural requirements (header: tenant branding; body: variable substitution visible; CTA button: brand color; footer: "Powered by Pilot").

---

### Decision 7 — Tenant Branding Settings IA Placement

**Decision**: `communications/` is a **new top-level settings group** added by FE-B14. It does not exist in FE-B11's settings IA (confirmed: settings dirs are `integrations/`, `my-account/`, `notifications/`, `operations/`, `sync-storage/`, `voice-ai/`).

**New settings IA additions by FE-B14**:
```
apps/web/src/app/(authed)/settings/
├── communications/
│   ├── layout.tsx                   # Communications nav section (owner/accountant only)
│   ├── page.tsx                     # Redirects → /settings/communications/email-branding
│   ├── email-branding/
│   │   └── page.tsx                 # Email branding settings (Decision 4 layout)
│   └── email-templates/
│       └── page.tsx                 # 16-template preview surface (Decision 6 layout)
```

**RBAC**: `settings.manage` for PUT/upload/test-send; `settings.view` for GET/preview. The `(authed)` layout guards JWT. The `communications/layout.tsx` uses `<RoleGate>` to restrict to `owner` and `accountant` roles (per spec §8: "owner + accountant access").

**Exact branding fields** (confirmed from `tenant_email_branding.py`):

| Field | Input type | Constraint | Save mode |
|:---|:---|:---|:---|
| Logo | File upload → S3 presigned URL | Max 5 MB; PNG/JPEG/WebP/GIF; recommended 400×100px | Explicit commit after upload |
| Brand color | Hex input (`#RRGGBB`) + color swatch | Valid hex; contrast warning if too light | `saveMode='blur'` via `SettingControl` |
| Email signature | Multi-line text (`inputType='string'`) | Max 500 chars | `saveMode='blur'` |
| Custom footer | Single-line text (`inputType='string'`) | Max 200 chars | `saveMode='blur'` |

**Color picker**: free hex input (not Pilot token palette). The tenant's brand color is their own branding, not constrained to Pilot's token system. A native `<input type="color">` paired with a text hex input provides a familiar picker UI without a third-party library dependency.

**Logo upload** follows the FE-B7 S3 photo upload pattern: `POST /settings/email-branding/logo-upload-url` → `{upload_url, s3_path}` → `PUT {upload_url}` directly from browser → `PATCH /settings/email-branding` with `{logo_s3_path}` to commit. Remove logo sets `logo_s3_path` to `null` via `PATCH`.

---

## Section A — Component Implementation Plan

### A.1 New Shared Components (`packages/ui/src/`)

#### `EmailBrandingPreview` (fleshed from FE-B1 skeleton) — **LOCKED by FE-B14**

**Location**: `packages/ui/src/email-branding-preview/EmailBrandingPreview.tsx` (in-place replacement)

**What changes**: the placeholder body is replaced with iframe rendering of `previewHtml`. The skeleton shimmer is preserved for `branding === null` and for `isLoading === true`. Three new optional props added to `EmailBrandingPreviewProps`.

**Backward compatibility**: FE-B1 skeleton usages pass only `branding`, `previewWidth`, `className`. Adding `templateKey`, `previewHtml`, `isLoading` as optional with sensible defaults (`undefined`, `undefined`, `false`) means all FE-B1 usages continue to work unchanged.

**New types** added to `packages/ui/src/email-branding-preview/types.ts`:
```typescript
export type EmailTemplateId =
  | 'welcome'
  | 'email_verification'
  | 'quote_sent'
  | 'quote_accepted'
  | 'quote_declined'
  | 'quote_expiring_soon'
  | 'invoice_sent'
  | 'payment_received_tenant'
  | 'payment_received_customer'
  | 'payment_failed'
  | 'subscription_renewal_receipt'
  | 'subscription_payment_failed'
  | 'trial_expiring_soon'
  | 'trial_expired'
  | 'password_reset'
  | 'mfa_reset_by_owner'
  | 'data_export_ready';

export const EMAIL_TEMPLATE_CATEGORIES: Record<EmailTemplateId, 'customer_facing' | 'internal'> = {
  quote_sent: 'customer_facing',
  quote_expiring_soon: 'customer_facing',
  invoice_sent: 'customer_facing',
  payment_received_customer: 'customer_facing',
  payment_failed: 'customer_facing',
  // all others: 'internal'
  ...
};
```

**Barrel export update** in `packages/ui/src/index.ts`: add `EmailTemplateId`, `EMAIL_TEMPLATE_CATEGORIES`, updated `EmailBrandingPreviewProps` to the FE-B1 export block.

#### `StripePaymentForm` types extension — **LOCKED by FE-B14**

**Location**: `packages/ui/src/stripe-payment/types.ts` (additive only)

Only two optional props added to `StripePaymentFormProps` (see Decision 1). `StripePaymentForm.tsx` itself is **not modified**.

---

### A.2 New Web Feature Components (`apps/web/src/features/`)

#### `public-quote/` — public quote page feature

```
apps/web/src/features/public-quote/
├── PublicQuotePage.tsx              # Server component: fetches + renders the full page
├── QuoteLineItemsTable.tsx          # Line items table (responsive: table on desktop, card stack on mobile)
├── QuoteAcceptModal.tsx             # Accept confirmation overlay with optional comment
├── QuoteDeclineModal.tsx            # Decline overlay: reason radio + optional comment
├── QuoteAcceptedState.tsx           # Post-accept confirmation view (state-aware revisit)
├── QuoteDeclinedState.tsx           # Post-decline confirmation view (state-aware revisit)
├── QuoteExpiredPage.tsx             # 90-day expiry / revoked link page with tenant contact
├── TenantBrandedHeader.tsx          # Logo + "From [tenant name]" header (reused by invoice)
├── PoweredByPilotFooter.tsx         # "Powered by Pilot for Trades" footer (reused by invoice)
└── types.ts                         # PublicQuotePageState, QuoteActionOverlayProps, etc.
```

#### `public-invoice/` — public invoice page feature

```
apps/web/src/features/public-invoice/
├── PublicInvoicePage.tsx            # Server component: fetches + renders
├── InvoicePaymentModal.tsx          # Amount selection + StripePaymentForm orchestrator
├── InvoiceAmountSelector.tsx        # Full/adjusted amount UI with variance display
├── InvoicePaidState.tsx             # Fully paid confirmation (state-aware revisit)
├── InvoicePartialPaidState.tsx      # Partial payment history + remaining balance
├── InvoicePaymentProcessing.tsx     # "Payment processing" advisory state
└── types.ts                         # PaymentModalState, AmountVariantSelection, etc.
```

#### `email-branding/` — tenant email branding settings panel

```
apps/web/src/features/email-branding/
├── EmailBrandingSettingsPanel.tsx   # Full settings panel composing SettingControl fields
├── LogoUploadField.tsx              # S3 presigned upload + preview/remove
├── BrandColorField.tsx              # Hex input + color swatch (native color picker)
├── EmailTemplatePreviewSurface.tsx  # Two-pane template list + iframe preview
└── types.ts                         # EmailBrandingFormState, LogoUploadState, etc.
```

---

### A.3 Mobile

Not applicable. Public quote/invoice pages are web-only (responsive, but delivered as web pages). Email branding settings are web-only (owner task). Mobile surfaces do not consume any FE-B14 components.

---

### A.4 New Routes

**Unauthenticated (outside `(authed)`):**

```
apps/web/src/app/
├── q/
│   └── [token]/
│       └── page.tsx          # /q/{token} — public quote page
├── i/
│   └── [token]/
│       └── page.tsx          # /i/{token} — public invoice page
└── link-expired/
    └── page.tsx              # /link-expired — shared expired/revoked generic fallback
```

**Authenticated (inside `(authed)/settings/`):**

```
apps/web/src/app/(authed)/settings/
└── communications/
    ├── layout.tsx             # /settings/communications — RoleGate: owner/accountant
    ├── page.tsx               # Redirects → /settings/communications/email-branding
    ├── email-branding/
    │   └── page.tsx           # /settings/communications/email-branding
    └── email-templates/
        └── page.tsx           # /settings/communications/email-templates
```

---

## Section B — Execution Order

| # | Item | Rationale | Est. Days |
|:---|:---|:---|:---:|
| 1 | **Public quote page** (`/q/[token]`) — fetch quote data, render line items table, tenant-branded header, accept/decline buttons, mobile-responsive layout, `generateMetadata`, 410/401 error branches | Simpler surface (no payment). Establishes `TenantBrandedHeader`, `PoweredByPilotFooter`, `QuoteLineItemsTable` reused by invoice. | 2 |
| 2 | **Public invoice page** (`/i/[token]`) — fetch invoice data, render line items, amount-due display, "Pay this invoice" CTA, alternative payment methods section, state-aware paid/partial states | Mirrors quote page structure. Reuses header/footer from step 1. | 2 |
| 3 | **Stripe one-time payment with amount variance** — `InvoicePaymentModal`: full/adjusted amount selector → `POST /payment-intent` → `<StripePaymentForm mode="one-time">` → `POST /confirm-payment` advisory → payment processing state | Core Stripe integration for this batch. | 2 |
| 4 | **State-aware revisit handling** — quote accepted/declined states, invoice paid/partial-paid states, expired-link page with tenant contact info, 410 vs 401 error branches | Spec'd robustness. Completes public pages. | 1 |
| 5 | **Customer comments (entity-bound)** — accept/decline overlays with 2000-char textarea, character counter, required comment validation for payment variance, comment display on revisit confirmation pages | Entity-bound; composable with steps 1–4 components. | 1.5 |
| 6 | **Tenant email branding settings** — `EmailBrandingSettingsPanel`: logo upload via S3 presigned URL, hex color picker, signature textarea, footer text, `saveMode='blur'` via `SettingControl`, test-send button, Communications settings IA group | Settings extension; establishes `communications/` nav group. | 2 |
| 7 | **16 email template visual review** — `EmailTemplatePreviewSurface`: two-pane layout, template list grouped by category, iframe preview pane, template selector wired to `POST /preview`, visual review against spec's structural requirements for each of 16 templates | Bulk verification work; requires branding settings complete (step 6). | 3 |
| 8 | **`EmailBrandingPreview` fleshed** — replace FE-B1 placeholder body with iframe rendering of `previewHtml`; add `templateKey`, `previewHtml`, `isLoading` props; wire into branding settings panel for live preview; update barrel export | Completes the FE-B1 → FE-B14 skeleton-to-fleshed lifecycle. | 1 |

**Total estimated**: 14.5–18 days (matches impl plan range of 14–18 days).

---

## Section C — API Contracts

### C.1 Public Quote Endpoints (no JWT)

**`GET /api/v1/public/quotes/{signed_token}`**
```typescript
// Response: PublicQuoteResponse
interface PublicQuoteResponse {
  quote_id: string;
  tenant_name: string;
  customer_name: string;
  quote_total_cents: number;
  currency: string;
  line_items: PublicLineItem[];
  status: 'sent' | 'accepted' | 'declined' | 'expired';
  expires_at: string | null;          // ISO 8601
  branding: { logo_url: string | null; brand_color_hex: string | null; };
  customer_acceptance_comment: string | null;
  customer_decline_comment: string | null;
}
interface PublicLineItem {
  description: string;
  quantity: string;
  unit_price_cents: number;
  total_cents: number;
}
// Error status codes:
// 410 GONE  — expired, revoked, or quote not found
// 401 UNAUTHORIZED — invalid/tampered token
```

**`POST /api/v1/public/quotes/{signed_token}/accept`**
```typescript
// Request body: { comment?: string }  // max 2000 chars (client validated)
// Response: { status: 'accepted'; accepted_at: string }
// Error: 409 CONFLICT — already accepted or declined
// Error: 410 GONE — expired/revoked
```

**`POST /api/v1/public/quotes/{signed_token}/decline`**
```typescript
// Request body: { reason: DeclineReason; comment?: string }
type DeclineReason = 'pricing' | 'scope' | 'timing' | 'other_contractor' | 'other';
// Response: { status: 'declined'; declined_at: string }
// Error: 409 CONFLICT — already accepted or declined
// Error: 422 UNPROCESSABLE — invalid reason value
```

---

### C.2 Public Invoice Endpoints (no JWT)

**`GET /api/v1/public/invoices/{signed_token}`**
```typescript
interface PublicInvoiceResponse {
  invoice_id: string;
  tenant_name: string;
  customer_name: string;
  invoice_total_cents: number;
  amount_paid_cents: number;
  amount_due_cents: number;
  currency: string;
  line_items: PublicLineItem[];
  status: 'unpaid' | 'partial' | 'paid';
  due_date: string | null;
  branding: { logo_url: string | null; brand_color_hex: string | null; };
}
```

**`POST /api/v1/public/invoices/{signed_token}/payment-intent`**
```typescript
// Request body:
interface PaymentIntentRequest {
  amount_cents: number;      // customer-selected amount (positive integer)
  comment?: string;          // REQUIRED by backend when amount_cents != invoice_total_cents
}
// Response:
interface PaymentIntentResponse {
  client_secret: string;         // Stripe Payment Intent client secret
  payment_intent_id: string;     // for confirm-payment advisory
}
// Error: 422 — comment missing when amount differs; amount <= 0
// Error: 410 — link expired/revoked/invoice not found
```

**`POST /api/v1/public/invoices/{signed_token}/confirm-payment`**
```typescript
// Request body: { payment_intent_id: string }
// Response: { status: 'pending_confirmation' }
// Advisory only — backend does NOT finalize payment here; webhook does
```

---

### C.3 Email Branding Endpoints (JWT required)

**`GET /api/v1/settings/email-branding`** → requires `settings.view`
```typescript
interface EmailBrandingResponse {
  tenant_id: string;
  logo_url: string | null;             // resolved S3 URL
  brand_color_hex: string | null;      // '#RRGGBB' or null (defaults to Pilot brand-indigo)
  email_signature: string | null;      // max 500 chars
  custom_footer: string | null;        // max 200 chars
}
```

**`PATCH /api/v1/settings/email-branding`** → requires `settings.manage`
```typescript
// Request body (all fields optional — PATCH semantics):
interface EmailBrandingUpdate {
  logo_s3_path?: string | null;
  brand_color_hex?: string | null;     // validated: '#RGB' or '#RRGGBB'
  email_signature?: string | null;
  custom_footer?: string | null;
}
// Response: EmailBrandingResponse
// Error: 422 — invalid hex format; signature > 500; footer > 200
```

**`POST /api/v1/settings/email-branding/logo-upload-url`** → requires `settings.manage`
```typescript
// Request: { content_type: 'image/png' | 'image/jpeg' | 'image/webp'; file_size_bytes: number }
// Response: { upload_url: string; s3_path: string }
// Error: 422 — unsupported content type; > 5 MB
```

**`POST /api/v1/settings/email-branding/preview`** → requires `settings.view`
```typescript
// Request: { template_id: EmailTemplateId }
// Response: { subject: string; body_html: string; body_plain: string }
// Error: 404 — unknown template_id
```

**`POST /api/v1/settings/email-branding/test-send`** → requires `settings.manage`
```typescript
// Request: (no body — sends to requesting user's email)
// Response: { status: 'sent'; to: string }
```

---

## Section D — State Management

### D.1 Stripe Payment Modal State Machine

The `InvoicePaymentModal` component manages the full payment flow:

```
                    ┌─────────────────────────────────────────────┐
                    │             InvoicePaymentModal              │
                    │                                              │
  [Pay invoice]     ▼                                              │
  ────────────►  AMOUNT_SELECT                                     │
                    │  Customer selects full or adjusted amount    │
                    │  Adjusted: comment required                  │
                    │                                              │
  [Continue]        ▼                                              │
  ────────────►  PI_LOADING                                        │
                    │  POST /payment-intent (amount, comment)      │
                    │  Loading spinner on modal                    │
                    │                                              │
  [client_secret]   ▼                                              │
  ────────────►  CARD_ENTRY                                        │
                    │  <StripePaymentForm mode="one-time">         │
                    │  Amount display shows selected amount        │
                    │                                              │
  [Pay $X.XX btn]   ▼                                              │
  ────────────►  SUBMITTING                                        │
                    │  stripe.confirmPayment() in progress         │
                    │  Button disabled, spinner active             │
                    │                                              │
          ┌─────────┤                                              │
          │         │                                              │
     [success]   [error]                                           │
          │         │                                              │
          ▼         ▼                                              │
     PROCESSING   CARD_ENTRY (inline error shown)                  │
          │         ──────────────────────────────►  [retry]      │
          │  POST /confirm-payment (advisory)                      │
          │  Shows "Payment processing — please wait"              │
          │                                                        │
          ▼                                                        │
     SUCCESS (webhook confirmed via page re-fetch)                 │
          │  Page transitions to InvoicePaymentConfirmation        │
          └─────────────────────────────────────────────────────  │
```

**State type**:
```typescript
type PaymentModalState =
  | { phase: 'amount-select'; selectedAmountCents: number; comment: string; adjusting: boolean }
  | { phase: 'pi-loading' }
  | { phase: 'card-entry'; clientSecret: string; paymentIntentId: string; selectedAmountCents: number }
  | { phase: 'submitting' }
  | { phase: 'processing'; paymentIntentId: string }
  | { phase: 'success'; amountPaidCents: number }
  | { phase: 'error'; error: string; recoverable: true };
```

---

### D.2 Amount Selection State

`InvoiceAmountSelector` internal state:

```typescript
interface AmountSelectorState {
  adjusting: boolean;                    // false = paying full amount_due_cents
  customAmountCents: number;             // editable when adjusting=true
  comment: string;                       // required when adjusting && customAmountCents != amount_due_cents
  commentError: string | null;           // "Comment is required when adjusting amount"
  amountError: string | null;            // "Amount must be greater than $0"
}
```

Variance display is derived:
```typescript
const varianceCents = customAmountCents - invoiceAmountDueCents;
const varianceIsPositive = varianceCents > 0;  // overpayment
const remainingCents = Math.max(invoiceAmountDueCents - customAmountCents, 0);
```

---

### D.3 Quote/Invoice Action Submit State

```typescript
type QuoteActionState =
  | { phase: 'idle' }
  | { phase: 'submitting' }
  | { phase: 'success'; acceptedAt?: string; declinedAt?: string }
  | { phase: 'error'; message: string; retryable: boolean };
```

Used by `QuoteAcceptModal` and `QuoteDeclineModal`. On success, parent `PublicQuotePage` transitions to show `QuoteAcceptedState` or `QuoteDeclinedState` via local state.

---

### D.4 `EmailBrandingPreview` Live Sync

The `EmailBrandingSettingsPanel` fetches a fresh preview after each field saves. The preview is NOT fetched during typing — only after blur-save confirms. Debounce is not needed since `SettingControl.onSave` already debounces via blur semantics.

```typescript
// In EmailBrandingSettingsPanel
const [previewHtml, setPreviewHtml] = useState<string | undefined>();
const [isPreviewLoading, setIsPreviewLoading] = useState(false);
const [previewTemplateKey, setPreviewTemplateKey] = useState<EmailTemplateId>('quote_sent');

// Called from every SettingControl.onSave callback:
async function refetchPreview() {
  setIsPreviewLoading(true);
  try {
    const res = await fetch('/api/v1/settings/email-branding/preview', {
      method: 'POST',
      body: JSON.stringify({ template_id: previewTemplateKey }),
    });
    const data = await res.json();
    setPreviewHtml(data.body_html);
  } finally {
    setIsPreviewLoading(false);
  }
}
```

---

## Section E — Error States

| Error | HTTP | UI Rendering | Token class |
|:---|:---|:---|:---|
| Signed URL expired (90-day window) | 410 GONE | `QuoteExpiredPage` / `InvoiceExpiredPage`: "This link has expired" + tenant name, phone, email, "Powered by Pilot" footer | `fault-50` bg, `fault-700` heading, `fault-200` divider |
| Signed URL revoked (manual revocation) | 410 GONE | Same expired page — revoked and expired are indistinguishable to the customer by design | Same as above |
| Signed URL invalid/tampered | 401 UNAUTHORIZED | Generic "Invalid link" page — no tenant contact info shown (tenant cannot be identified from tampered token) | `fault-50` bg, `fault-600` text |
| Quote not found (deleted/archived) | 410 GONE | Same expired page treatment | Same as expired |
| Quote already accepted (409) | 409 CONFLICT | `QuoteAcceptModal` surface: "This quote was already accepted on [date]." Modal closes; page shows `QuoteAcceptedState` | `neutral-50` bg with margin-600 checkmark |
| Quote already declined (409) | 409 CONFLICT | Same: "This quote was already declined." Show `QuoteDeclinedState` | `neutral-50` bg |
| Stripe card declined | Stripe error | Inline error below `PaymentElement` via `StripePaymentForm.onError`: "Card declined. Try a different card or contact your bank." | `fault-600` text (established in FE-B13 Section H) |
| Stripe generic error | Stripe error | "An unexpected error occurred. Please try again." with retry affordance. `PaymentModal` stays on `CARD_ENTRY` phase. | `fault-600` text |
| Payment Intent creation failed (422) | 422 | `PI_LOADING` → `AMOUNT_SELECT` with error banner: "Could not initiate payment. [error detail]." | `fault-50` banner, `fault-700` text |
| Comment required for variance (422) | 422 — frontend prevented | Frontend blocks submission when `adjusting && !comment`. No network call made. Error: "Please explain why you're paying a different amount." | `fault-600` beneath textarea |
| Amount ≤ 0 | client-only | "Amount must be greater than $0." Submission blocked. | `fault-600` beneath amount input |
| Logo upload file too large | client-only + 422 | "Logo must be smaller than 5 MB." Both pre-validated on file select. | `fault-600` beneath upload field |
| Logo upload unsupported type | client-only + 422 | "Upload a PNG, JPEG, or WebP image." | `fault-600` |
| Email branding save failure | 422 / 500 | `SettingControl` `onSave` throws → `phase: 'error'` → inline error beneath field, draft value rolled back | `fault-600` |
| Email preview render failure | 404 / 500 | Preview pane shows: "Could not load preview. [template_id] may not be available." with retry button | `fault-600` |
| Test-send email failure | 422 / 500 | Toast notification (via `NotificationQueueProvider`): "Test email could not be sent. Try again." | `fault-600` notification severity |

---

## Section F — TypeScript Interfaces

### F.1 `StripePaymentFormProps` Additive Extension (LOCKED for Phase 2)

```typescript
// packages/ui/src/stripe-payment/types.ts — ADDITIVE ADDITIONS ONLY
// Existing props unchanged (stripePublishableKey, clientSecret, mode,
// paymentAmountCents, submitLabel, onSuccess, onError, onLoadingChange, disabled, testID)

export interface StripePaymentFormProps {
  // ... existing locked props from FE-B13 ...

  /** FE-B14 ADDITION: invoice token for constructing return_url on redirect flows */
  invoiceToken?: string;
  /** FE-B14 ADDITION: additional callback with actual payment amount for invoice reconciliation */
  onPaymentSuccess?: (result: StripePaymentResult & { actualAmountPaidCents: number }) => void;
}
```

---

### F.2 `EmailBrandingPreviewProps` (LOCKED by FE-B14)

```typescript
// packages/ui/src/email-branding-preview/types.ts

export interface TenantBranding {         // FE-B1 (unchanged)
  primaryColorHex: string;
  logoUrl: string | null;
  senderName: string;
  replyToEmail: string;
}

export interface EmailBrandingPreviewProps {
  branding: TenantBranding | null;        // FE-B1 — null shows shimmer placeholder
  previewWidth?: number;                  // FE-B1 — default 560px
  className?: string;                     // FE-B1

  // FE-B14 ADDITIONS (all optional — backward-compatible):
  templateKey?: EmailTemplateId;          // which template to preview; default 'quote_sent'
  previewHtml?: string;                   // server-rendered HTML for iframe; undefined = placeholder
  isLoading?: boolean;                    // true shows loading skeleton over preview pane
}
```

---

### F.3 `PublicQuoteData`

```typescript
// apps/web/src/features/public-quote/types.ts

export interface PublicQuoteData {
  quoteId: string;
  tenantName: string;
  customerName: string;
  quoteTotalCents: number;
  currency: string;
  lineItems: PublicLineItem[];
  status: 'sent' | 'accepted' | 'declined' | 'expired';
  expiresAt: string | null;
  branding: PublicTenantBranding;
  customerAcceptanceComment: string | null;
  customerDeclineComment: string | null;
}

export interface PublicTenantBranding {
  logoUrl: string | null;
  brandColorHex: string;               // never null in UI — falls back to '#5B3FF0' (Pilot indigo)
}

export interface PublicLineItem {
  description: string;
  quantity: string;
  unitPriceCents: number;
  totalCents: number;
}
```

---

### F.4 `PublicInvoiceData`

```typescript
// apps/web/src/features/public-invoice/types.ts

export interface PublicInvoiceData {
  invoiceId: string;
  tenantName: string;
  customerName: string;
  invoiceTotalCents: number;
  amountPaidCents: number;
  amountDueCents: number;
  currency: string;
  lineItems: PublicLineItem[];
  status: 'unpaid' | 'partial' | 'paid';
  dueDate: string | null;
  branding: PublicTenantBranding;
}
```

---

### F.5 `CustomerCommentRequest`

```typescript
// Used for both quote accept/decline and payment variance comment
export interface QuoteAcceptRequest {
  comment?: string;     // max 2000 chars; optional
}

export interface QuoteDeclineRequest {
  reason: DeclineReason;
  comment?: string;     // max 2000 chars; optional
}

export type DeclineReason =
  | 'pricing'
  | 'scope'
  | 'timing'
  | 'other_contractor'
  | 'other';

export interface PaymentIntentRequest {
  amountCents: number;
  comment?: string;     // required by backend when amountCents != invoiceTotalCents
}
```

---

### F.6 `EmailBrandingSettings`

```typescript
// apps/web/src/features/email-branding/types.ts

export interface EmailBrandingSettings {
  tenantId: string;
  logoUrl: string | null;
  brandColorHex: string | null;     // null = use Pilot default
  emailSignature: string | null;
  customFooter: string | null;
}

export interface EmailBrandingFormState {
  logoUrl: string | null;
  logoS3Path: string | null;
  brandColorHex: string;            // never null in form — defaults to '#3B43D6'
  emailSignature: string;
  customFooter: string;
}

export interface LogoUploadState {
  phase: 'idle' | 'requesting-url' | 'uploading' | 'committing' | 'success' | 'error';
  error: string | null;
  previewUrl: string | null;
}
```

---

### F.7 `PaymentAmountVariant`

```typescript
export interface PaymentAmountVariant {
  adjusting: boolean;
  selectedAmountCents: number;   // equals amountDueCents when !adjusting
  varianceCents: number;         // selectedAmountCents - invoiceTotalCents
  comment: string;               // required when varianceCents != 0
}

export function derivePaymentVariance(
  selectedCents: number,
  invoiceTotalCents: number
): { varianceCents: number; remainingCents: number; isOverpayment: boolean } {
  const varianceCents = selectedCents - invoiceTotalCents;
  return {
    varianceCents,
    remainingCents: Math.max(invoiceTotalCents - selectedCents, 0),
    isOverpayment: varianceCents > 0,
  };
}
```

---

### F.8 `EmailTemplate` (16-template inventory type)

```typescript
export interface EmailTemplate {
  id: EmailTemplateId;
  displayName: string;
  category: 'customer_facing' | 'internal';
  triggerDescription: string;
  audience: 'customer' | 'tenant_user' | 'any_user';
  contentSlots: EmailContentSlot[];
}

export interface EmailContentSlot {
  slotKey: string;               // e.g. 'greeting', 'body', 'cta_label', 'cta_url'
  description: string;
  variables: string[];           // e.g. ['{{customer_name}}', '{{quote_total}}']
  maxChars: number | null;
  isTomAuthored: boolean;        // true = final copy owned by Tom as pre-launch hygiene
}

// Catalog for development reference — not runtime (backend owns canonical templates)
export const EMAIL_TEMPLATE_CATALOG: EmailTemplate[] = [
  {
    id: 'quote_sent',
    displayName: 'Quote sent',
    category: 'customer_facing',
    triggerDescription: 'Tenant sends a quote to customer',
    audience: 'customer',
    contentSlots: [
      { slotKey: 'subject', description: 'Email subject line', variables: ['{{tenant_name}}', '{{quote_number}}'], maxChars: 200, isTomAuthored: true },
      { slotKey: 'greeting', description: 'Opening line', variables: ['{{customer_name}}'], maxChars: 500, isTomAuthored: true },
      { slotKey: 'body', description: 'Main body', variables: ['{{quote_total}}', '{{quote_expiry_date}}'], maxChars: 2000, isTomAuthored: true },
      { slotKey: 'cta_label', description: 'CTA button text', variables: [], maxChars: 50, isTomAuthored: true },
      { slotKey: 'cta_url', description: 'Public quote URL', variables: ['{{quote_url}}'], maxChars: null, isTomAuthored: false },
    ],
  },
  // ... (remaining 15 templates with analogous slot definitions)
];
```

---

## Section G — Test Plan

**Test subfolder**: `apps/web/__tests__/batch_fe_b14/`
**Test stack**: Vitest + React Testing Library (unit/integration), Playwright (E2E)

### G.1 Unit Tests (target: 50+)

**Public quote page** (12 tests):
- `QuoteLineItemsTable` renders all line items with correct `unit_price_cents` / `total_cents` formatting
- `QuoteLineItemsTable` renders mobile card-stack layout when viewport < 640px
- `TenantBrandedHeader` renders `logoUrl` when provided; falls back to tenant name in bold when `logoUrl` null
- `TenantBrandedHeader` applies `brandColorHex` CSS variable to accent elements
- `QuoteAcceptModal` renders comment textarea with `47 / 2000` counter on input
- `QuoteAcceptModal` does not block submission when comment is empty (optional for accept)
- `QuoteDeclineModal` renders reason radio group with all 5 options
- `QuoteDeclineModal` comment is optional; textarea renders with counter
- `QuoteAcceptedState` displays `accepted_at` date and customer comment when present
- `QuoteDeclinedState` displays decline reason label and comment when present
- `QuoteExpiredPage` renders with `fault-50` background and tenant contact info
- `PublicQuotePage` does not call `useAuth()` (static analysis test — import check)

**Public invoice page** (10 tests):
- `InvoicePaidState` renders "PAID" status badge with `margin-50` background
- `InvoicePartialPaidState` renders `amount_paid_cents` history and "Pay remaining $X" affordance
- `InvoicePaymentModal` starts in `AMOUNT_SELECT` phase with `amountDueCents` pre-filled
- `InvoiceAmountSelector` shows variance row when `adjusting = true` and custom amount entered
- `InvoiceAmountSelector` shows positive variance row when overpayment entered
- `InvoiceAmountSelector` blocks submission when `adjusting && !comment` (comment error shown)
- `InvoiceAmountSelector` blocks submission when `selectedAmountCents <= 0`
- `InvoiceAmountSelector` comment textarea does NOT appear when paying full amount (`adjusting = false`)
- `PublicInvoicePage` renders "Pay this invoice" CTA for unpaid invoice
- `PublicInvoicePage` renders "Pay remaining $X" for partial invoice

**`InvoicePaymentModal` state machine** (8 tests):
- Transitions `amount-select` → `pi-loading` on "Continue to payment" click
- Returns to `amount-select` with error banner on `POST /payment-intent` failure
- Transitions `pi-loading` → `card-entry` on successful PI response, passes `client_secret` to `StripePaymentForm`
- Transitions `card-entry` → `submitting` on form submit
- Transitions `submitting` → `processing` on `StripePaymentForm.onSuccess`
- Transitions `submitting` → `card-entry` on `StripePaymentForm.onError` (inline Stripe error visible)
- Transitions `card-entry` → `card-entry` on Stripe card-declined error (does NOT close modal)
- `processing` state renders "Payment processing — please wait" copy

**`EmailBrandingPreview` fleshed** (6 tests):
- Renders shimmer skeleton when `branding === null`
- Renders shimmer skeleton when `isLoading === true` even if `previewHtml` present
- Renders iframe `srcDoc={previewHtml}` when `previewHtml` provided
- Renders placeholder text when `branding` provided but `previewHtml` undefined
- Template selector dropdown fires `onTemplateChange` callback with selected `templateKey`
- iframe has `sandbox="allow-same-origin"` attribute (security guard)

**Email branding settings** (8 tests):
- `LogoUploadField` calls `POST /logo-upload-url` on file select
- `LogoUploadField` blocks files > 5 MB before network call
- `LogoUploadField` blocks non-image file types
- `BrandColorField` validates hex format on blur: rejects `#ZZZZZ`, accepts `#3B43D6`
- `BrandColorField` updates color swatch live as hex input changes
- `EmailBrandingSettingsPanel` calls `refetchPreview` after each `SettingControl.onSave`
- `EmailBrandingSettingsPanel` "Send test email" button fires `POST /test-send` and shows success toast
- `EmailTemplatePreviewSurface` renders all 16 templates in list; preview pane updates on row click

**`StripePaymentForm` FE-B13 regression** (6 tests):
- Subscription mode usage: `onSuccess(result)` fires without `onPaymentSuccess` present
- `invoiceToken` prop is undefined in subscription mode — no behavioral change
- One-time mode: `onPaymentSuccess` callback fires with `{ paymentIntentId, actualAmountPaidCents }` when provided
- One-time mode: `onSuccess` still fires (backward compat) even when `onPaymentSuccess` present
- FE-B13 signup wizard subscription path renders with new `StripePaymentFormProps` type without TS errors
- FE-B14 invoice modal passes `invoiceToken` prop without TS errors

---

### G.2 Integration Tests (target: 14+)

1. **Full public quote → accept with comment** — fetch quote → render page → open accept modal → type comment → submit → `POST /accept` fires with `{comment}` → page transitions to `QuoteAcceptedState` showing comment
2. **Full public quote → decline with reason + comment** — fetch quote → open decline modal → select "Pricing" → type comment → submit → page shows `QuoteDeclinedState` with reason and comment
3. **Full public invoice → Stripe full payment** — fetch invoice (unpaid) → click "Pay this invoice" → modal opens in `amount-select` → keep full amount → click Continue → mock `POST /payment-intent` returns client_secret → `StripePaymentForm` renders → mock Stripe confirms → `POST /confirm-payment` fires → transition to `processing` → `InvoicePaymentConfirmation`
4. **Full public invoice → Stripe partial payment with comment** — modal opens → tick "Adjust amount" → enter custom amount → comment textarea appears → type comment → Continue → `POST /payment-intent` includes `{amount_cents, comment}` → confirmation
5. **Backend rejects partial payment without comment (422)** — frontend validation catches before API call; test confirms no network request fired when `adjusting=true && !comment`
6. **Expired link → renders `QuoteExpiredPage`** — mock API returns 410 → page shows `fault-50` page with tenant contact info from response headers; does NOT show action buttons
7. **Invalid/tampered link → renders generic error** — mock API returns 401 → generic error page (no tenant contact info)
8. **Quote state-aware revisit (already accepted)** — fetch accepted quote (`status: 'accepted'`) → renders `QuoteAcceptedState` directly, no accept/decline buttons visible
9. **Invoice state-aware revisit (partial paid)** — fetch partial invoice (`status: 'partial'`) → renders `InvoicePartialPaidState` with payment history and "Pay remaining" affordance
10. **Email branding settings panel saves on blur** — render panel → change `emailSignature` → tab away (blur) → `PATCH /email-branding` fires → `refetchPreview` fires → new `previewHtml` loaded into `EmailBrandingPreview`
11. **Logo upload flow** — select file → `POST /logo-upload-url` → PUT to mock S3 → `PATCH /email-branding` with `logo_s3_path` → `EmailBrandingPreview` shows logo
12. **Template preview selector** — select "Invoice sent" from dropdown → `POST /preview` fires with `{template_id: 'invoice_sent'}` → iframe `srcDoc` updates
13. **Test-send email** — click "Send test email to my address" → `POST /test-send` fires → success toast appears via `NotificationQueueProvider`
14. **All 16 template preview endpoints respond** — integration test iterates all 16 `EmailTemplateId` values → each `POST /preview` returns non-empty `body_html` → each rendered in iframe without JS errors

---

### G.3 E2E Tests (target: 3+)

1. **Customer flow: view invoice → Stripe payment → receive confirmation** — using Stripe test mode keys and test card `4242 4242 4242 4242`; visits `/i/{token}` → pays full amount → Stripe webhook fires → page polls for status → "Payment received" confirmation displayed with correct amount
2. **Expired link handling end-to-end** — generate an expired signed token (with past `expires_at`) → visit `/q/{token}` → confirm expired page renders with `fault-50` background and tenant contact info; no accept/decline buttons
3. **Email branding visual review** — visit `/settings/communications/email-branding` → upload PNG logo → change brand color to `#FF6B35` → change signature → preview pane updates with new branding for all 16 templates iteratively (sample check on 3: `quote_sent`, `invoice_sent`, `welcome`)

---

## Section H — Token Audit

FE-B14 introduces a new category of visual surface: **tenant-branded customer-facing pages**. These pages use the tenant's `brandColorHex` for primary accents, not Pilot's design tokens. The token audit clearly distinguishes the two categories.

### H.1 Tenant-Branding Elements (CSS variables, not Pilot tokens)

Customer-facing page elements that use tenant branding are styled using CSS custom properties derived from the `brandColorHex` field in the API response:

```typescript
// TenantBrandedHeader.tsx — inline style approach
const brandStyle = {
  '--tenant-brand': branding.brandColorHex,     // e.g. '#3B43D6'
  '--tenant-brand-dark': darkenHex(branding.brandColorHex, 0.15),
} as React.CSSProperties;
```

**Elements that use `--tenant-brand`**:
- Accept button background on public quote page
- "Pay this invoice" CTA background on public invoice page
- Heading underline accent on public quote/invoice pages
- CTA button inside customer-facing email templates (rendered server-side by template engine — not a frontend concern, but noted for completeness)
- Tenant logo accent bar in `TenantBrandedHeader`

**These elements do NOT use Pilot token classes** (e.g., `bg-brand-600`). They use inline styles or CSS variables derived from the tenant's free-hex branding.

### H.2 Pilot-Token Elements (always use Pilot design tokens)

All Pilot chrome on public pages uses Pilot tokens. No hardcoded hex values.

| Element | Token class | Location |
|:---|:---|:---|
| Stripe error text | `text-fault-600` | `StripePaymentForm` inline error (FE-B13 established) |
| Stripe submit button | `bg-brand-600 hover:bg-brand-800` | `StripePaymentForm` (FE-B13 established) |
| Expired/revoked link page background | `bg-fault-50` | `QuoteExpiredPage`, `InvoiceExpiredPage` |
| Expired/revoked link page heading | `text-fault-700` | Same pages |
| "Already paid" / "Already accepted" success state bg | `bg-margin-50` | `InvoicePaidState`, `QuoteAcceptedState` |
| "Already paid" / "Already accepted" success badge | `text-margin-700` | Same components |
| Comment submit button (accept/decline overlays) | `bg-brand-600 hover:bg-brand-800 text-white` | `QuoteAcceptModal`, `QuoteDeclineModal` |
| Comment validation error | `text-fault-600` | Beneath textarea in overlays |
| "Powered by Pilot for Trades" footer text | `text-neutral-400` | `PoweredByPilotFooter` |
| Email branding settings panel — all `SettingControl` instances | FE-B11 established tokens | `EmailBrandingSettingsPanel` |
| Test-send success toast | `severity='success'` via `NotificationQueueProvider` | FE-B11 notification banner tokens |
| Logo upload error | `text-fault-600` | `LogoUploadField` |
| Preview loading skeleton | `bg-neutral-200 animate-pulse` | `EmailBrandingPreview` skeleton (FE-B1 established) |
| Processing state text | `text-neutral-600` | `InvoicePaymentProcessing` |

### H.3 "Powered by Pilot for Trades" Footer

The footer is a shared `PoweredByPilotFooter` component used on both public quote and public invoice pages. It renders at the bottom of every public page regardless of tenant branding.

```tsx
// PoweredByPilotFooter.tsx
export function PoweredByPilotFooter() {
  return (
    <p className="text-center text-xs text-neutral-400 mt-8 pb-6">
      Powered by{' '}
      <a
        href="https://pilotfortrades.com"
        target="_blank"
        rel="noopener noreferrer"
        className="text-neutral-500 hover:text-neutral-700 underline"
      >
        Pilot for Trades
      </a>
    </p>
  );
}
```

---

## Section I — Downstream Contract Lock

FE-B14 has no downstream batch dependents. The following locks are established for **Phase 2** use:

### I.1 `StripePaymentForm` One-Time Mode — Phase 2 Lock

The one-time invoice payment mode of `StripePaymentForm` is the **canonical Pilot invoice payment interface**. Any Phase 2 payment surface (multi-invoice payment, installment plans, overpayment refund flow) must:
- Consume `StripePaymentForm mode="one-time"` as the Stripe Elements boundary
- Pass `clientSecret` obtained from a backend Payment Intent endpoint
- NOT wrap with `<Elements>` externally (RULE 1)

Phase 2 additions that are explicitly NOT permitted:
- Adding a second Stripe Elements boundary in any other component
- Importing `@stripe/react-stripe-js` in any file other than `StripePaymentForm.tsx`
- Forking `StripePaymentForm` for a different payment context

### I.2 `EmailBrandingPreview` — Phase 2 Lock

`EmailBrandingPreviewProps` is LOCKED as defined in Section F.2. Phase 2 additions must be optional and additive only. Specifically locked for Phase 2 reuse:
- MMS attachment preview surface (if added, composes `EmailBrandingPreview` with `templateKey='invoice_sent'`)
- Full template editing UI (if added, feeds rendered HTML as `previewHtml` from a draft-render endpoint)

### I.3 Public Page Infrastructure — Phase 2 Reservation

The `TenantBrandedHeader`, `PoweredByPilotFooter`, and `QuoteLineItemsTable` components are the canonical customer-facing rendering primitives. Phase 2 customer portal (if authentication is added) must compose these same components. No fork.

Phase 2 items explicitly deferred (per spec §15 Deferred Items):
- Customer registration / full customer accounts
- Comment replies from tenant to customer on entity-bound comments
- Full email template editing by tenants
- Customer dashboard with multi-quote history
- PDF/print-friendly view of public quote/invoice
- Multi-language customer-facing pages
- Custom domain for tenant short links (Phase 2: `mike.electrics` custom domain)
- Stripe Connect for direct-to-tenant payment routing

### I.4 Settings IA — Communications Group

`/settings/communications/` is a new group introduced by FE-B14. Future settings sub-surfaces for Phase 2 (e.g., SMS template customization, customer notification preferences) slot into this group. FE-B14 establishes `communications/layout.tsx` as the navigation anchor with `RoleGate` access control.

---

## Implementation Notes for React Engineer

1. **Never call `useAuth()`** in `/q/[token]/page.tsx` or `/i/[token]/page.tsx`. These are fully unauthenticated surfaces. The `(authed)` layout does not wrap them. Any auth context import in these files must be rejected in code review.

2. **HTTP error handling pattern**: On `GET /public/quotes/{token}`, the Next.js page component must distinguish 410 vs 401 responses:
   - 410 → render `QuoteExpiredPage` component (includes tenant contact from error response metadata if available)
   - 401 → render generic invalid-link error (no tenant info)
   - Other → generic error state

3. **`StripePaymentForm` is not modified**. The invoice payment flow wraps it externally via `InvoicePaymentModal`. Do not add amount variance logic inside `StripePaymentForm.tsx`.

4. **S3 logo upload** follows the FE-B7 pattern exactly: `POST /logo-upload-url` → direct browser PUT to presigned URL → `PATCH /email-branding` with `logo_s3_path`. Do not proxy the binary through the FastAPI backend.

5. **`generateMetadata`** on public pages must add `robots: 'noindex, nofollow'` — these are customer-specific documents and must not be indexed.

6. **`EmailBrandingPreview` iframe**: use `sandbox="allow-same-origin"` but NOT `allow-scripts`. The server-rendered HTML templates do not require JavaScript. This prevents XSS if a template ever contains unescaped content.

7. **Tenant brand color fallback**: when `branding.brand_color_hex` is `null`, use `#3B43D6` (Pilot brand-indigo). This is consistent with the backend default in `public_quotes.py` (`"#5B3FF0"` is a typo in the code — the spec says `#3B43D6` for Pilot brand-indigo; raise with backend team).
