# Pilot for Trades Design System — Pass 4, Tier 4 #13: Customer-Facing Public Quote/Invoice Link Styling Pass

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Customer-facing public quote and invoice link pages (no Pilot login required), email template designs for all transactional emails (16 templates), tenant email branding customization, Stripe integration for one-time invoice payment with amount variance, entity-bound customer comments on accept/decline/payment.
**Depends On**: Flow 4 (customer comms) · Flow 5 (quote approval) · Tier 1.5 (customer SMS) · Tier 3 #10 (Stripe subscription integration as parallel pattern) · `mvp-arch.md` Quoting/Sales schema (quote_public_link exists) · Invoicing/Billing schema (invoice_public_link exists)
**Backend additions**: A80 (signed URL infrastructure for public links), A81 (Stripe one-time payment for invoices with variance), A82 (email template rendering pipeline + tenant brand customization), A83 (quote/payment customer comment storage)
**Deliverable shape**: Shape E (Visual design + content composition) per Pass 4 framework doc — covers visual treatment plus content slot inventory for templates that Tom owns the final copy for

---

## Purpose

This is the only Pilot surface a non-Pilot user sees. The customer who receives a quote or invoice from Mike doesn't have a Pilot login; they click a link in an email or SMS, land on a Pilot-hosted page, view/accept/decline/pay the document. Their entire impression of Pilot — and by extension, of Mike's professionalism — is shaped by this surface.

The strategic frame: **the customer experience belongs to the tenant, not Pilot**. The page is tenant-branded prominently with a small "Powered by Pilot" footer. Customer-facing email templates use the tenant's logo, brand color, signature, and footer. From the customer's perspective, they're interacting with Mike's Electrical Services. Pilot is the invisible infrastructure.

This spec covers three workstreams plus their backend infrastructure:

1. **Public quote view** — the page customers land on when receiving a quote (with accept/decline + comment + email verification of the access path)
2. **Public invoice view** — the page customers land on when receiving an invoice (with Stripe-powered payment + amount variance + comment)
3. **Email template designs** — visual framework + 16 templates with content slots Tom fills in

Plus tenant-level email branding customization (`Settings > Communications > Email branding`) so each tenant's emails look like the tenant's emails, not Pilot's.

## Strategic direction

### Tenant-branded with subtle Pilot footer

Per Q2 in our scoping, customer-facing surfaces show the tenant's branding prominently — logo, business name, brand color, signature line. A small "Powered by Pilot for Trades" footer link sits at the bottom (with a link to pilotfortrades.com for customers who become curious about the platform).

The tenant's brand assets come from `Settings > Communications > Email branding` (Decision 12 below). For tenants who haven't customized, system defaults render with the tenant's name in plain text plus generic professional styling.

### Signed URL is the only authentication

Per the simplified model: customer clicks the link in their email and lands directly on the document. No additional verification, no 6-digit codes, no email re-confirmation. The signed URL itself is the authentication.

This matches the standard B2B SaaS pattern (DocuSign, Stripe payment links, HelloSign all work this way). The customer's email inbox is the verification mechanism — they clicked the link from their email, so they have access to that email account, which is sufficient implicit verification.

URL expiration: 90 days from generation. After expiration, customer hits a "This link has expired — contact [tenant] for a new one" page.

### Comments are entity-bound, not communication-channel-bound

Per your direction: customer comments on accept/decline/payment are stored on the entity (the quote, the payment) — not routed into the customer comm thread (Tier 1.5). This is the right architecture because:

- The comment IS the action context (the explanation accompanying accept/decline/payment), not a separate message
- Comments need review in the entity's context (office admin reviewing recent quotes; reviewing payment variance), not in chronological message thread
- One-way for MVP — customer comments to tenant; if tenant wants to reply, they use existing Customer Comms (Tier 1.5)

Comments trigger notifications per Tier 2 #5 "Customer activity" category. Owners and admins can act on the comment by reviewing the entity, revising the quote, etc.

### Email branding is structured customization, not full template editing

Per Q5b in our scoping, tenants customize their emails through structured controls: logo upload, brand color picker, signature text, footer text. Tenants cannot rewrite the email body. This avoids:
- Moderation risk (tenant inserting harmful content into customer emails)
- Rendering complexity (tenant writing markup that breaks email rendering)
- Tenant unhappiness when their custom template breaks after a Pilot template update

Phase 2 may add full template editing if observed user demand justifies. MVP keeps it bounded.

### Stripe one-time payment parallel to subscription pattern

Tier 3 #10 / A76 introduced Stripe Subscriptions for tenant subscription billing. This spec introduces Stripe one-time payment for invoice payment — same Stripe account, parallel API surface (Stripe Payment Intents instead of Subscriptions). Tenant doesn't have to set up payment processing separately; uses the same Stripe customer record they already have.

Customer enters card via Stripe Elements; Stripe processes the payment; Pilot records the payment with the actual amount paid; invoice balance updates accordingly.

## Locked design decisions

### 1. Public quote view — visual layout

**Decision**: The public quote URL is `https://app.pilotfortrades.com/q/{signed-token}` where the signed token contains the quote ID, customer ID, expiration timestamp, and a cryptographic signature. The page renders without requiring login.

#### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Tenant logo]                                          From [tenant name]│
│ ────────────                                                             │
│                                                                          │
│ Quote QU-1024                                                            │
│ ─────────────                                                            │
│                                                                          │
│ For: Sarah Johnson · 1234 Main Street, San Francisco, CA                 │
│ Date: April 27, 2026                                                     │
│ Expires: May 11, 2026                                                    │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ Items                                                                    │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ Description              Qty    Price        Total                  │  │
│ │ 200A Panel Upgrade        1     $3,200       $3,200                 │  │
│ │   200A main breaker panel                                            │  │
│ │   Code-compliant grounding                                           │  │
│ │                                                                     │  │
│ │ 12-2 Romex Wire           250   $0.85/ft     $212.50                │  │
│ │ Permit fee                1     $185         $185                   │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│ Subtotal:                                                  $3,597.50    │
│ Tax (7.25%):                                                 $260.82    │
│ ──────────────                                                          │
│ Total:                                                     $3,858.32    │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ Notes from [tenant name]                                                 │
│ Standard 30-day workmanship warranty included.                           │
│ Materials warranty per manufacturer.                                     │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ Signed by: [tenant name signature]                                       │
│ [Tenant phone] · [Tenant email]                                          │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ ┌────────────────────────────┐  ┌────────────────────────────┐          │
│ │ Accept this quote          │  │ Decline                    │          │
│ │ Move forward with the work │  │ Not the right fit          │          │
│ └────────────────────────────┘  └────────────────────────────┘          │
│                                                                          │
│                                            ─                             │
│                                                                          │
│                          Powered by Pilot for Trades                     │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Visual treatment

- **Tenant logo** at top-left (uploaded via Email branding settings; falls back to tenant name in heavy weight if no logo)
- **Brand color accent** on the heading underline, action button background, and tax line — drawn from tenant brand color setting (defaults to Pilot brand-indigo if not customized)
- **Item table** with clean rows, neutral borders
- **Total** prominently styled in larger weight
- **Tenant signature block** — name, phone, email; replicates the formal-quote feel
- **Two action buttons** — Accept (primary, brand color) and Decline (secondary, neutral border)
- **Powered by Pilot footer** — small, neutral text; links to pilotfortrades.com in a new tab

#### Mobile rendering

The page is fully responsive. Mobile rendering stacks the layout vertically:
- Tenant logo + name on top
- Quote header
- Items table becomes vertically-stacked cards (Description / Qty / Price / Total per item)
- Total prominently displayed
- Action buttons full-width, stacked vertically

**Rationale**: clean professional layout that emphasizes the document content and the tenant's brand. The customer doesn't see Pilot's marketing voice or product framing — they see a professional quote from a contractor. Mobile rendering preserves the same visual hierarchy adapted for phone width.

### 2. Quote acceptance flow

**Decision**: When the customer clicks "Accept this quote," a confirmation overlay appears with optional comment field:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Accept Quote QU-1024 ($3,858.32)                                         │
│ ────────────────────                                                     │
│                                                                          │
│ Add a comment (optional):                                                │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ "Let's get started ASAP — when can you begin?"                   │    │
│ │                                                                  │    │
│ │                                                                  │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ 47 / 2000 characters                                                     │
│                                                                          │
│ By accepting, you agree to the work and pricing above.                   │
│                                                                          │
│                                              [Cancel]  [Confirm accept] │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Comment field

- 2,000-character maximum (per our scoping)
- Optional — customer can leave blank
- Plain text — no rich text formatting

#### Confirmation behavior

- Customer clicks "Confirm accept" → request sends to API
- Loading state during commit
- On success, page transitions to acceptance confirmation:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ✓ Quote accepted                                                         │
│                                                                          │
│ [Tenant name] has been notified. They'll be in touch about next steps.   │
│                                                                          │
│ Quote QU-1024 — Total: $3,858.32                                         │
│ Accepted on April 27, 2026 at 2:14 PM                                    │
│                                                                          │
│ Your comment:                                                            │
│ "Let's get started ASAP — when can you begin?"                           │
│                                                                          │
│ A copy of this confirmation has been emailed to you.                     │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Tenant notification

- Tenant receives push + email per Tier 2 #5 "Customer activity" category default
- Notification body includes the comment (or "No comment left" if blank)
- Tenant clicks notification → navigates to the quote detail page in Pilot, which now shows the acceptance + comment prominently

#### Already-accepted handling

If the customer clicks the accept button on a quote that has already been accepted (perhaps by clicking the link a second time), the page shows the acceptance confirmation directly with "This quote was accepted on [date] by [customer email]." No way to re-accept.

**Rationale**: optional comment captures context without forcing it. Confirmation overlay prevents accidental clicks. Post-accept page provides receipt-like confirmation. Tenant notification with comment in body gives the office admin the context to act on the comment immediately.

### 3. Quote decline flow

**Decision**: When the customer clicks "Decline," similar confirmation overlay with comment:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Decline Quote QU-1024                                                    │
│ ─────────────────────                                                    │
│                                                                          │
│ Tell [tenant name] why (optional but helpful):                           │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ "Can you remove item 3 (permit fee)? We'll handle that ourselves.  │   │
│ │ Then it looks fine."                                             │    │
│ │                                                                  │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ 88 / 2000 characters                                                     │
│                                                                          │
│ Reason for declining:                                                    │
│ ◯ Pricing                                                                │
│ ◯ Scope of work                                                          │
│ ◯ Timing                                                                 │
│ ◯ Going with another contractor                                          │
│ ● Other                                                                  │
│                                                                          │
│                                              [Cancel]  [Confirm decline]│
└─────────────────────────────────────────────────────────────────────────┘
```

#### Reason categorization

A radio-button list captures structured decline reason:
- Pricing
- Scope of work
- Timing
- Going with another contractor
- Other

This metadata helps tenants understand decline patterns over time (Phase 2 reporting). For MVP, just stored on the decline record.

#### Confirmation behavior

Similar to acceptance — loading state, success page, tenant notification with comment.

#### Acceptance after decline

Once a quote is declined, the customer sees the decline confirmation if they revisit the link. They cannot un-decline. If the tenant revises the quote based on the comment, they generate a new quote and send a new link — the original quote stays in declined state.

**Rationale**: structured + free-text decline gives tenants both quick categorization (declined for pricing) and rich context (the specific feedback). One-click decline without context wastes the moment.

### 4. Public invoice view — visual layout

**Decision**: The public invoice URL is `https://app.pilotfortrades.com/i/{signed-token}` with the same signed token model as quotes.

#### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Tenant logo]                                          From [tenant name]│
│ ────────────                                                             │
│                                                                          │
│ Invoice INV-2026-0341                                                    │
│ ──────────────────                                                       │
│                                                                          │
│ For: Sarah Johnson · 1234 Main Street, San Francisco, CA                 │
│ Date: April 27, 2026                                                     │
│ Due: May 11, 2026                                                        │
│ Reference: Quote QU-1024 (accepted April 27, 2026)                       │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ Items                                                                    │
│ [Same item table format as quote]                                        │
│                                                                          │
│ Subtotal:                                                  $3,597.50    │
│ Tax (7.25%):                                                 $260.82    │
│ ──────────────                                                          │
│ Amount due:                                                $3,858.32    │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ Pay this invoice                                                 │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│ Or                                                                       │
│ • Mail check to: [tenant address]                                        │
│ • Bank transfer details: contact [tenant phone]                          │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ Signed by: [tenant name signature]                                       │
│ [Tenant phone] · [Tenant email]                                          │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│                          Powered by Pilot for Trades                     │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Differences from quote view

- "Amount due" instead of "Total"
- "Pay this invoice" prominent CTA (brand color)
- Alternative payment methods listed below ("Or — mail check, bank transfer") for customers who prefer not to use Stripe
- Reference to the originating quote when applicable (clickable link if customer wants to verify)

#### Already-paid handling

If invoice is fully paid and customer revisits the link, page shows:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Tenant logo]                                          From [tenant name]│
│                                                                          │
│ Invoice INV-2026-0341                                                    │
│ Status: ✓ PAID                                                           │
│                                                                          │
│ Paid on April 28, 2026 — $3,858.32 via credit card                       │
│                                                                          │
│ [Receipt details]                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

Partial-paid handling: if customer paid partial amount with comment, the invoice page shows the unpaid balance with both "Pay remaining $X" and "Pay different amount" affordances.

**Rationale**: invoice view emphasizes payment as the primary action while preserving alternative payment paths for customers who don't want to pay online. Already-paid state shows confirmation; partial-paid state shows balance with options.

### 5. Stripe payment flow with amount variance

**Decision**: Clicking "Pay this invoice" opens a payment modal using Stripe Elements:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Pay Invoice INV-2026-0341                                                │
│ ─────────────────────────                                                │
│                                                                          │
│ Amount due: $3,858.32                                                    │
│                                                                          │
│ Pay amount: $ [3858.32]                                                  │
│ ☐ Adjust amount (pay more or less)                                       │
│                                                                          │
│ Card details:                                                            │
│ [Stripe Elements card input]                                             │
│                                                                          │
│ Billing address:                                                         │
│ [Stripe Elements address input]                                          │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │ Today's payment: $3,858.32                                       │    │
│ │ This will be sent to [tenant name].                              │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│                                                  [Cancel]  [Pay $3,858.32]│
└─────────────────────────────────────────────────────────────────────────┘
```

#### Amount adjustment flow

If customer ticks "Adjust amount":

```
Pay amount: $ [3472.49]                                                  │
Variance: -$385.83 (10% less than invoice total)                         │
                                                                          │
Comment (required when amount differs from invoice):                      │
┌──────────────────────────────────────────────────────────────────┐    │
│ "I get a 10% discount per our agreement, paying 90% now."         │    │
└──────────────────────────────────────────────────────────────────┘    │
                                                                          │
Today's payment: $3,472.49                                                │
Remaining balance after this payment: $385.83                             │
```

#### Comment requirement

When amount differs from invoice total (either over or under), the comment field is required. Customer cannot proceed to payment without entering an explanation. 2,000 character maximum.

For overpayment ("here's a tip for Tom"), the customer pays more; the comment provides context; the variance is recorded as overpayment (handled per accounting practice — could be applied to the next invoice, refunded, etc., per the tenant's process).

For underpayment, the customer pays less; the comment explains; the unpaid balance remains on the invoice.

#### Stripe transaction handling

- Stripe Elements collects card details; PCI-compliant; raw card never touches Pilot servers
- Payment is processed for the actual amount the customer entered (not necessarily the invoice total)
- Pilot records the payment with `amount_paid_cents`, `invoice_total_cents`, `variance_cents`, `customer_payment_comment`
- Stripe webhook confirms successful payment; invoice updates to reflect the payment

#### Tenant notification

- Tenant receives push + email per Tier 2 #5 "Billing" category default
- Notification body shows the actual amount paid + variance + comment if any
- Notification routes to the payment detail in Pilot

#### Payment failure

If Stripe declines the card, error displays inline (Tier 3 #8/#9 Er2 — validation error treatment): "Card declined. Try a different card or contact your bank." Customer can retry without leaving the page.

**Rationale**: amount adjustment with required comment captures the customer's reasoning at the moment of payment, which is much higher quality than asking the tenant to chase down "why did you pay less?" later. Stripe handles the card processing safely; Pilot just records what actually happened.

### 6. Quote/invoice access expiration

**Decision**: Public links expire 90 days from generation. After expiration, the customer hits a friendly "link expired" page:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ This link has expired                                                    │
│ ─────────────────────                                                    │
│                                                                          │
│ The link to this quote/invoice is no longer active.                      │
│                                                                          │
│ Contact [tenant name] to get a fresh link:                               │
│ • Phone: [tenant phone]                                                  │
│ • Email: [tenant email]                                                  │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│                          Powered by Pilot for Trades                     │
└─────────────────────────────────────────────────────────────────────────┘
```

The page surfaces the tenant's contact info so the customer can request a fresh link without confusion. No automated re-issuance — tenant has to manually re-send (which is the right behavior, since 90-day-old quotes/invoices may need updating).

Tenant can also manually revoke a link at any time (e.g., if quote was sent to wrong customer) — same expired-page treatment for revoked links.

**Rationale**: 90-day expiration handles the common case (customer responding within reasonable time) without leaving signed URLs valid forever. Manual re-issuance ensures the tenant verifies the recipient and the document state before sending again.

### 7. Email template framework

**Decision**: All transactional emails use a consistent template framework that renders with the tenant's branding settings. 16 templates in MVP:

| # | Template | Audience | Trigger |
| :--- | :--- | :--- | :--- |
| 1 | Welcome / signup confirmation | Tenant owner | Tenant signup completion |
| 2 | Email verification code | Any user | Email verification request |
| 3 | Quote sent | Customer | Tenant sends quote |
| 4 | Quote accepted | Tenant | Customer accepts quote |
| 5 | Quote declined | Tenant | Customer declines quote |
| 6 | Quote expiring soon | Customer | 3 days before quote expiration |
| 7 | Invoice sent | Customer | Tenant sends invoice |
| 8 | Payment received | Tenant + Customer (receipt) | Stripe payment success |
| 9 | Payment failed | Customer | Stripe payment failure |
| 10 | Subscription renewal receipt | Tenant | Stripe subscription renewal |
| 11 | Subscription payment failed | Tenant | Stripe subscription payment failure |
| 12 | Trial expiring soon | Tenant | Per Tier 3 #10 trial expiration warnings |
| 13 | Trial expired | Tenant | Per Tier 3 #10 trial expiration |
| 14 | Password reset | Any user | Password reset request |
| 15 | MFA reset by owner | Affected user | Per Tier 2 #7 owner reset of user MFA |
| 16 | Data export ready | Requesting user | Per Tier 2 #7 data export completion |

#### Template framework structure

All templates share:

- **Header**: tenant logo (or tenant name if no logo) + tenant brand color accent
- **Body**: template-specific content with variable substitution (e.g., `{{customer_name}}`, `{{quote_total}}`, `{{tenant_name}}`)
- **CTA button** (when applicable): brand-colored primary action — "View quote," "Pay invoice," "Reset password," etc.
- **Footer**: tenant signature line + contact info + "Powered by Pilot for Trades" small link
- **Plain text fallback**: every template has a text-only version for clients that don't render HTML

#### Customer-facing vs internal templates

Six templates are customer-facing (sent to customers, not tenant users):
- 3 Quote sent
- 6 Quote expiring soon
- 7 Invoice sent
- 8 Payment received (the receipt copy)
- 9 Payment failed

These render with the tenant's full email branding (logo, brand color, signature, footer).

The remaining 10 templates are internal (sent to tenant users):
- 1 Welcome, 2 Email verification, 4 Quote accepted, 5 Quote declined, 8 Payment received (the tenant copy), 10–13 Subscription/trial events, 14 Password reset, 15 MFA reset, 16 Data export ready

Internal templates use Pilot's standard branding (Pilot logo, neutral professional treatment), not tenant branding. This is appropriate because the tenant is the recipient — they don't need to see their own branding back at them.

#### Variable substitution model

Each template defines its variables and the values come from runtime context. For example, `{{customer_name}}` substitutes from the customer record at send time. `{{tenant_logo_url}}` substitutes from the tenant's email branding settings. `{{quote_url}}` is the signed URL for that specific quote.

A82 below covers the rendering pipeline.

#### Content authoring

Final email copy is content/legal work that Tom owns per pre-launch hygiene track. This spec reserves the structural slots (subject, greeting, body, CTA, signature, footer); copy fills in. For development, placeholder copy ("Quote sent — see attached link") is acceptable.

**Rationale**: one consistent framework with per-template content slots is far cheaper than 16 unique designs. Customer-facing branding for customer recipients; Pilot branding for tenant recipients. Clear separation produces consistent email experience without confusing brand mixing.

### 8. Tenant email branding settings

**Decision**: A new sub-page at `Settings > Communications > Email branding` (owner + accountant access per Settings IA framework Decision 8) lets tenants customize their customer-facing email branding.

#### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Email branding                                                           │
│ ──────────────                                                           │
│                                                                          │
│ How your customer-facing emails look. Internal emails (password reset,   │
│ etc.) use Pilot's standard branding.                                     │
│                                                                          │
│ Logo                                                                     │
│ ┌───────────────────────────────────────────────────────────────────┐   │
│ │ [Logo preview / placeholder]              [Upload]  [Remove]      │   │
│ │ Recommended: 400×100px PNG with transparent background. Max 500KB. │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ Brand color                                                              │
│ [#3B43D6] [Color picker]   Used for buttons and accents in emails.       │
│                                                                          │
│ Email signature                                                          │
│ ┌───────────────────────────────────────────────────────────────────┐   │
│ │ [Multi-line text input]                                           │   │
│ │ "Mike Johnson · Mike's Electrical Services                         │   │
│ │ (415) 555-0123 · mike@mikes-electric.example.com"                         │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ Custom footer (optional)                                                 │
│ ┌───────────────────────────────────────────────────────────────────┐   │
│ │ "Licensed & insured · CA Lic #C10-000000"                         │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│ Appears in the footer of every customer email above the                  │
│ "Powered by Pilot" line.                                                 │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ Preview                                                                  │
│ ┌───────────────────────────────────────────────────────────────────┐   │
│ │ [Live preview of an email rendered with current branding]         │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│ [Send test email to my address]                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Logo upload

- Upload via standard file input → S3 presigned URL pattern (consistent with profile photo from Tier 2 #7)
- Image processed server-side to fit recommended dimensions
- Tenant can preview, replace, or remove
- Removed logo falls back to tenant name in heavy text weight

#### Brand color

- Hex color picker (familiar React color picker component)
- Defaults to Pilot brand-indigo (#3B43D6) if tenant hasn't customized
- Validated for sufficient contrast against white background (warns if too light to read on email backgrounds)

#### Signature

- Multi-line plain text input, 500 character maximum
- Preserves line breaks
- Renders in customer-facing email footers (above "Powered by Pilot")

#### Custom footer

- Optional plain text, 200 character maximum
- Renders in email footer above signature
- Useful for license numbers, regulatory disclosures, etc.

#### Preview and test

- Live preview shows rendered email using the current settings
- "Send test email to my address" button sends a sample email (using the welcome template structure as a generic preview) to the owner's email address
- Useful for verifying rendering across email clients

#### Save behavior

- Save-on-blur per Settings IA framework Decision 5 (each field saves independently when changed)
- Logo upload is explicit save (file upload requires commit step)
- Optimistic UI per Tier 2 #4 patterns

**Rationale**: structured customization gives tenants meaningful branding control without the complexity of full template editing. Logo + brand color + signature + custom footer are the four levers that produce real visual differentiation. Live preview + test email handle the verification need without requiring tenant to manually trigger emails.

### 9. Customer email comment flow

**Decision**: Comments on quote accept/decline and invoice payment are stored on the entity per our scoping. Implementation:

#### Quote acceptance comment

- New column `quote.customer_acceptance_comment TEXT NULL`
- New column `quote.customer_accepted_at TIMESTAMPTZ NULL`
- Captured at the moment of acceptance via Decision 2
- Visible on the quote detail page in Pilot:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Quote QU-1024 — ACCEPTED                                                 │
│                                                                          │
│ Accepted by Sarah Johnson on April 27, 2026 at 2:14 PM                   │
│                                                                          │
│ Customer comment:                                                        │
│ "Let's get started ASAP — when can you begin?"                           │
│                                                                          │
│ [...rest of quote detail]                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Quote decline comment

- New column `quote.customer_decline_comment TEXT NULL`
- New column `quote.customer_decline_reason TEXT NULL` (enum: pricing | scope | timing | other_contractor | other)
- New column `quote.customer_declined_at TIMESTAMPTZ NULL`
- Captured at the moment of decline via Decision 3
- Visible on the quote detail page with similar prominent display

#### Invoice payment comment

- New column `payment.customer_payment_comment TEXT NULL`
- New column `payment.amount_variance_cents INTEGER NULL` — populated when amount paid differs from invoice total
- Captured at the moment of payment via Decision 5
- Visible on the payment detail page and on the related invoice detail:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Payment received — Invoice INV-2026-0341                                 │
│                                                                          │
│ Amount: $3,472.49 (variance: -$385.83 from $3,858.32 invoice total)      │
│ Method: Credit card via Stripe                                           │
│ Date: April 28, 2026 at 9:32 AM                                          │
│                                                                          │
│ Customer comment:                                                        │
│ "I get a 10% discount per our agreement, paying 90% now."                │
│                                                                          │
│ Outstanding invoice balance: $385.83                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Notifications

Comments trigger notifications per Tier 2 #5 "Customer activity" category. Owners and admins receive push + email per their preferences. Notifications include the comment in the body.

#### One-way comments — tenant response uses existing customer comms

If the tenant wants to respond to a customer comment (e.g., "Sure, I can start Tuesday"), they use existing customer comms (Tier 1.5 SMS or email reply). This spec doesn't add reply infrastructure to the entity-bound comment model. Comments are one-way; conversation is via the comm channels.

**Rationale**: entity-bound storage matches the actual semantics — these comments ARE the action context. Visible prominently on the entity detail in Pilot's UI ensures office admins see the comment when reviewing the entity, not buried in a separate comm thread. One-way for MVP keeps scope controlled.

### 10. Already-acted-upon revisit handling

**Decision**: When a customer revisits a public link after they've already taken the action, the page shows the current state cleanly:

| Entity | Original state | Revisit state |
| :--- | :--- | :--- |
| Quote not yet acted upon | Accept/Decline buttons visible | Same as original |
| Quote accepted | (action taken) | Page shows acceptance confirmation with date + customer comment if any |
| Quote declined | (action taken) | Page shows decline confirmation with reason + comment if any |
| Quote expired | (auto-state change) | Expired page (per Decision 6) |
| Invoice not yet paid | Pay button visible | Same as original |
| Invoice partially paid | Pay button shows remaining balance | Page shows payment history + remaining balance + Pay options |
| Invoice fully paid | (action taken) | Page shows fully-paid confirmation with payment history |

The intent: customer should never see an action button for an action they've already completed. They see the resulting state and any relevant history/details.

**Rationale**: prevents accidental double-actions. The link is the same URL; the page renders state-aware.

### 11. SMS-link variant for customer comms

**Decision**: When a tenant sends a quote or invoice via Customer Comms (Tier 1.5 SMS), the SMS includes the public link in shortened form:

```
From [tenant name]: Your quote is ready. View and accept here: pilot.tr/q/aXk29
```

The shortened URL (`pilot.tr/q/{short-code}`) is a Pilot-managed redirect that resolves to the full signed URL. This:

- Reduces SMS character usage (shorter URL = fewer segments)
- Provides cleaner customer experience
- Allows tracking SMS link clicks separately from email link clicks (Phase 2 analytics)

#### Short-link infrastructure

- New domain `pilot.tr` (or similar — TBD; Tom owns domain registration as pre-launch hygiene)
- Short codes are 5–8 character base62 strings
- Resolves to signed full URL with same expiration semantics
- Click tracking captures referrer / user-agent for Phase 2 analytics

This is a small Phase 2 reservation in the architecture; for MVP, full URLs in SMS are acceptable if the short-link infrastructure isn't ready. Worth flagging because A80 below specifies the optional short-link layer.

**Rationale**: short links are standard practice for SMS to reduce friction. Pilot-owned domain (vs. third-party shortener like bit.ly) ensures reliability and avoids exposure of customer URLs to third parties.

### 12. Tax and accounting integrity for variance payments

**Decision**: When a customer pays an amount that differs from invoice total, accounting integrity is preserved:

- **Underpayment**: invoice balance updates to `invoice_total - amount_paid`. Remaining balance is recorded as accounts receivable. QuickBooks sync (Tier 1 #2) reflects the partial payment naturally — QB native model handles partial payments.

- **Overpayment**: customer paid more than invoice total. The variance is recorded as `payment.amount_variance_cents` (positive value). Tenant reviews and decides: refund via Stripe, apply to future invoice, or accept as tip/gift. UI shows the variance prominently with action affordances.

#### Customer-side handling

- Customer sees their actual payment amount confirmed
- If underpayment, they see the remaining balance with "Pay remaining $X" affordance on revisit (Decision 10)
- If overpayment, they see "Paid $X (over invoice total by $Y)" with no further action — tenant handles

#### Tenant-side handling

- Tenant sees the actual payment amount in their payment record
- Variance + comment together provide context for accounting decisions
- Tenant can reconcile via QuickBooks or by issuing a refund/credit

This is standard accounting practice. No special edge-case handling needed.

**Rationale**: respects accounting integrity. Customer's actual payment is what's recorded; variance is metadata for the tenant's accounting process. QB sync handles partial payments natively.

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| Tenant-branded customer-facing pages with Pilot footer | **NEW** | — |
| Signed URL as authentication for public access | **NEW** | — |
| Entity-bound customer comments (vs. comm-thread routing) | **NEW** | — |
| Stripe one-time payment with amount variance | **NEW** | A76 (Stripe Subscriptions) — parallel pattern |
| Required comment when payment differs from invoice | **NEW** | — |
| Email template framework with structured tenant customization | **NEW** | — |
| Customer-facing vs internal email branding split | **NEW** | — |
| Pilot-managed short-link infrastructure | **NEW** | — |
| State-aware revisit handling for public links | **NEW** | — |
| Live email preview with test-send | **NEW** | — |
| Mobile-responsive customer-facing pages | Reused | Pass 1 design tokens |

## Cross-domain considerations

### A. Pre-launch hygiene integration — significant content authoring

This spec hosts more pre-launch hygiene content than any other Pass 4 surface:
- 16 transactional email templates' final copy
- Welcome email tone-setting copy
- Customer-facing email signature and footer defaults (used when tenants haven't customized)
- "Powered by Pilot" footer link copy and pilotfortrades.com landing
- Privacy policy footer link inclusion in customer-facing emails
- ToS reference inclusion in legal-relevant emails (subscription, account)

Tom owns content authoring; this spec reserves the structural slots. Content review can land independently of design lock.

### B. Stripe one-time payment vs Stripe Subscriptions

Tier 3 #10 / A76 introduced Stripe Subscriptions for tenant subscription billing. Tier 4 #13 / A81 introduces Stripe Payment Intents for one-time invoice payment. Same Stripe account; same Stripe customer record; different API surfaces.

Architectural note: Stripe Connect (Stripe's marketplace product) would let each tenant have their own Stripe account, with payments going directly to the tenant. For MVP, Pilot uses a single Stripe account and disburses to tenants via separate financial infrastructure (TBD). Phase 2 may move to Stripe Connect for cleaner direct-to-tenant payment flow.

This is a significant architectural decision that affects backend design. For MVP, single Stripe account model is simpler. Tom should review the Stripe Connect option before MVP launch — if Pilot needs to disburse customer payments to tenants, the model affects all downstream financial work.

### C. SMS link via Tier 1.5

When a tenant sends quote or invoice via SMS, the customer comm template includes the public link. Tier 1.5 already supports template-based outbound messaging; this spec extends template content to include public link variables.

The Tier 1.5 customer SMS infrastructure is not modified — public links flow through the existing Tier 1.5 send pipeline as message body content.

### D. Email branding settings inventory

The new tenant settings introduced by this spec (logo URL, brand color, signature, custom footer) live in `Settings > Communications > Email branding`. They should be added to:
- Settings IA framework's per-setting parity matrix (mobile read-only or web-only? Recommendation: web-only since branding management is owner-task best done at desk)
- Tier 2 #4 settings inventory
- A52 settings catalog

These touch-ups land at Pass 4 close.

### E. Notification preferences integration

Customer comments on quote/invoice/payment trigger notifications under Tier 2 #5 "Customer activity" category. Defaults from Tier 2 #5 Decision 3 apply. Owners and admins receive notifications per their preferences.

The forced-minimum push for Customer activity (Tier 2 #5 Decision 4) applies to inbound SMS replies specifically — customer comments via public link are NOT forced-minimum because they're batch-reviewable rather than real-time-actionable. Standard notification preferences apply.

### F. Audit log

Every customer-side action (view, accept, decline, pay) is captured in audit log per Settings IA framework Cross-Domain G. Captured events:
- Quote viewed via public link
- Quote accepted with timestamp + comment + customer email
- Quote declined with timestamp + reason + comment + customer email
- Invoice viewed via public link
- Invoice payment attempted (success or failure)
- Payment completed with amount + variance + comment

Customer email is captured for audit even though no Pilot account exists for the customer — provides the audit trail for "who acted on this quote."

### G. Help/about/feedback (Tier 4 #14) integration

The "Powered by Pilot for Trades" footer link in customer-facing emails and pages routes to `pilotfortrades.com` (the marketing site, owned by Tom as separate work). This isn't a Pilot product surface; it's the marketing landing for prospective customers who become curious.

Tier 4 #14 covers in-app help/about/feedback for Pilot users — different surface from this customer-facing one.

### H. Already-paid quotes can convert to PAID invoice via Stripe webhook

When a customer pays via Stripe, the webhook (per A76 / A81) confirms payment success. The invoice transitions to PAID state. If QuickBooks integration is enabled, the payment syncs to QB per Tier 1 #2.

The customer's revisit-handling (Decision 10) shows the paid state correctly because all state transitions go through the webhook → state update flow.

## Deferred items (Phase 2 / for future iteration)

- **Customer registration with full account access** — explicitly removed from MVP per your direction
- **Comment replies from tenant back to customer** — Phase 2 (use existing Customer Comms for now)
- **Full email template editing by tenants** — Phase 2 (structured customization in MVP)
- **Customer dashboard with multi-quote history** — Phase 2; depends on customer registration
- **Customer notifications about their own quotes/invoices** — Phase 2; depends on customer registration
- **SMS-only invoice/quote send** — Phase 2; MVP requires email path
- **Customer self-service decline reason customization** — Phase 2; fixed reason list in MVP
- **Bulk quote/invoice send to customer list** — Phase 2
- **Stripe Connect for direct-to-tenant payment** — Phase 2 architectural review
- **Multi-language customer-facing pages and emails** — Phase 2 with multi-language UI
- **Customer-facing analytics** ("opened quote 3 times before accepting") — Phase 2
- **Custom domain for tenant short links** (e.g., `mike.electrics`) — Phase 2
- **PDF download of quote/invoice from public page** — Phase 2 (customer-friendly artifact for offline review)
- **Print-friendly view of public quote/invoice** — Phase 2
- **Save / bookmark affordance for customers without registration** — Phase 2
- **Tenant logo recommendations / templates** — Phase 2
- **A/B test of customer-facing copy variants** — Phase 2 with analytics
- **Quote / invoice expiration custom intervals (currently fixed at 90 days)** — Phase 2

## Validation checklist

Before implementation begins:

- [ ] Public quote view layout implemented per Decision 1
- [ ] Quote acceptance flow with optional comment per Decision 2
- [ ] Quote decline flow with reason category + optional comment per Decision 3
- [ ] Public invoice view layout per Decision 4
- [ ] Stripe Elements integration for invoice payment per Decision 5
- [ ] Amount variance with required comment per Decision 5
- [ ] 90-day link expiration with friendly expired page per Decision 6
- [ ] Email template framework with 16 templates per Decision 7
- [ ] Customer-facing vs internal template branding split per Decision 7
- [ ] Tenant email branding settings UI per Decision 8
- [ ] Logo upload / brand color picker / signature / footer in branding settings per Decision 8
- [ ] Live email preview + test-send-to-my-address per Decision 8
- [ ] Quote/invoice customer comment columns per Decision 9
- [ ] Notification triggers for comments per Decision 9
- [ ] State-aware revisit handling per Decision 10
- [ ] SMS short-link infrastructure per Decision 11 (or full URL fallback for MVP)
- [ ] Variance payment accounting integrity per Decision 12
- [ ] Audit log captures all customer-side actions per Cross-Domain F
- [ ] Email content authoring underway per pre-launch hygiene track
- [ ] Stripe one-time payment integration tested with edge cases (under, over, exact, declined card)

## Backend additions (new for Tier 4 #13)

### A80. Signed URL Infrastructure for Public Quote/Invoice Links

**Triggered by**: Decisions 1, 4, 6, 11 — public access via signed URLs with 90-day expiration plus optional SMS short-link support.

**Scope**:

**Schema** (extends existing):
- `quote_public_link` and `invoice_public_link` tables already exist per arch doc
- Add columns to both: `signed_token TEXT NOT NULL` (URL-safe signed token), `expires_at TIMESTAMPTZ NOT NULL`, `revoked_at TIMESTAMPTZ NULL`, `created_by_user_id UUID NOT NULL`
- New table `public_link_short_code`:
  - `short_code TEXT PRIMARY KEY` (5–8 char base62 random)
  - `link_type TEXT` (`quote | invoice`)
  - `link_id UUID FK` — references quote_public_link or invoice_public_link
  - `created_at TIMESTAMPTZ`
  - Unique constraint enforces collision avoidance

**Token generation**:
- HMAC-signed token using a per-deployment secret
- Payload includes: link_id, link_type, expiration, customer_id (for verification)
- Tokens are URL-safe base64-encoded
- Verification at request time validates signature + expiration + revocation status

**Public access endpoints**:
- `GET /api/v1/public/quotes/{signed_token}` — returns quote payload for rendering
- `POST /api/v1/public/quotes/{signed_token}/accept` — accept quote with optional comment
- `POST /api/v1/public/quotes/{signed_token}/decline` — decline quote with reason + comment
- `GET /api/v1/public/invoices/{signed_token}` — returns invoice payload for rendering
- `POST /api/v1/public/invoices/{signed_token}/payment-intent` — initiate Stripe Payment Intent (per A81)

**Short-link redirect**:
- `GET /api/v1/short/{short_code}` — resolves short code to signed URL and 302-redirects
- Domain configuration: `pilot.tr` or similar Pilot-owned short domain (TBD; Tom owns)
- Click tracking captures user-agent and IP for Phase 2 analytics

**Revocation**:
- `POST /api/v1/quotes/{quote_id}/public-link/revoke` — manually revoke (RBAC: tenant user with quote access)
- Revocation invalidates the signed URL immediately; subsequent access shows expired page

**No customer authentication** — clicking the link IS the access. The signed URL is the credential.

**Effort estimate**: Medium — 4 days. Token generation/verification + endpoints + short-link infrastructure (if pilot.tr domain ready) + revocation.

### A81. Stripe One-Time Payment for Invoices with Amount Variance

**Triggered by**: Decisions 4, 5, 12 — Stripe payment integration for invoice payment with variance handling.

**Scope**:

**Stripe Payment Intents integration**:
- Frontend uses Stripe Elements (card input + address input) on the public invoice page
- Backend creates Stripe Payment Intent for the customer-entered amount
- Customer-entered amount can differ from invoice total; comment is required by frontend validation when amount differs
- On successful payment confirmation from Stripe webhook, Pilot records the payment

**Schema**:
- Existing `payment` table extended:
  - `stripe_payment_intent_id TEXT`
  - `customer_payment_comment TEXT NULL`
  - `amount_variance_cents INTEGER NULL` — calculated as `amount_paid - invoice_total` (negative for underpayment, positive for over)
  - `paid_via TEXT` — `stripe | check | bank_transfer | other`

**Stripe webhook handler**:
- Existing webhook endpoint from A76 extended to handle Payment Intent events:
  - `payment_intent.succeeded` — record payment, update invoice balance, trigger notification
  - `payment_intent.payment_failed` — surface failure to customer-facing UI
- Invoice balance calculation: `invoice_total - sum(payments_amount_paid)`
- For underpayment (variance < 0), invoice remains in `partial` state with remaining balance
- For overpayment (variance > 0), variance flagged for tenant review (UI shows "Customer paid $X over invoice total — review")

**APIs**:
- `POST /api/v1/public/invoices/{signed_token}/payment-intent` — creates Stripe Payment Intent for the customer-entered amount; returns Stripe client secret for frontend
- `POST /api/v1/public/invoices/{signed_token}/confirm-payment` — frontend calls after Stripe Elements confirms; backend reconciles with webhook

**Stripe Connect consideration**:
- For MVP: single Stripe account model; payments accumulate in Pilot's Stripe account; disbursement to tenant is separate financial process (TBD)
- Phase 2: evaluate Stripe Connect for direct-to-tenant payment routing
- This is an architectural decision Tom should review before MVP launch

**Effort estimate**: Medium — 4–5 days. Stripe Payment Intents + webhook integration + variance handling + accounting reconciliation.

### A82. Email Template Rendering Pipeline + Tenant Brand Customization

**Triggered by**: Decisions 7, 8 — 16 email templates with structured tenant customization.

**Scope**:

**Schema**:
- New table `email_template`
  - `template_id TEXT PRIMARY KEY` (e.g., `quote_sent`, `invoice_sent`, `payment_received`, `welcome`, etc.)
  - `display_name TEXT`
  - `category TEXT` — `customer_facing | internal`
  - `subject_template TEXT` (with variable substitution)
  - `body_html_template TEXT`
  - `body_plain_template TEXT` — text fallback
  - `variables JSONB` — list of supported variables for this template
  - `is_active BOOLEAN`

- New table `tenant_email_branding`
  - `tenant_id UUID PK`
  - `logo_s3_path TEXT NULL`
  - `brand_color_hex TEXT NULL` — defaults to Pilot brand-indigo if null
  - `email_signature TEXT NULL`
  - `custom_footer TEXT NULL`
  - `updated_at TIMESTAMPTZ`

**Template seed data**:
- 16 templates seeded at deployment with placeholder copy
- Tom updates with final copy as pre-launch hygiene work proceeds
- Templates can be edited at the platform level via direct DB updates (operator admin work)

**Rendering pipeline** (`services/email_template_renderer.py`):
- Takes template_id + context payload
- Resolves variables from context: customer name, quote total, signed URL, etc.
- For customer-facing templates: applies tenant branding (logo, color, signature, footer) from `tenant_email_branding`
- For internal templates: uses Pilot standard branding
- Renders both HTML and plain text variants
- Returns ready-to-send email payload for SendGrid

**Tenant branding endpoints**:
- `GET /api/v1/settings/email-branding` — returns current branding for tenant
- `PUT /api/v1/settings/email-branding` — update branding; logo upload uses S3 presigned URL pattern
- `POST /api/v1/settings/email-branding/test-send` — send test email to requesting user's address using current branding settings

**Logo upload** (consistent with Tier 2 #7 profile photo pattern):
- Frontend requests presigned S3 URL
- Frontend uploads to S3
- Backend processes (resize to 400x100 max with transparent background preservation)
- `tenant_email_branding.logo_s3_path` updated

**Live preview**:
- `POST /api/v1/settings/email-branding/preview` — returns sample email rendered with current branding settings (uses welcome template structure as preview content)

**Effort estimate**: Medium — 4–5 days. Template schema + 16 template seeds + rendering pipeline + tenant branding endpoints + logo upload + live preview. Template content authoring is Tom's work, not part of this estimate.

### A83. Quote/Payment Customer Comment Storage with Notifications

**Triggered by**: Decision 9 — entity-bound customer comments with notifications.

**Scope**:

**Schema** (extends existing):
- Add to `quote` table:
  - `customer_acceptance_comment TEXT NULL`
  - `customer_accepted_at TIMESTAMPTZ NULL`
  - `customer_decline_comment TEXT NULL`
  - `customer_decline_reason TEXT NULL` — enum: `pricing | scope | timing | other_contractor | other`
  - `customer_declined_at TIMESTAMPTZ NULL`
  - `customer_email_at_action TEXT NULL` — captured at action time for audit
- Add to `payment` table:
  - `customer_payment_comment TEXT NULL`
  - `amount_variance_cents INTEGER NULL` (already added per A81 schema; same column)

**Action handlers**:
- Quote accept handler (called by A80 acceptance endpoint): updates quote columns + triggers notification
- Quote decline handler: updates quote columns + triggers notification
- Payment handler (already covered by A81): notification on successful payment with comment included if present

**Notifications**:
- Per Tier 2 #5 "Customer activity" category
- Notification body templates include comment text when present
- Push + email per recipient preferences

**UI rendering** (frontend; not backend addition but flagged for completeness):
- Quote detail page shows acceptance/decline comment prominently when present
- Payment detail page shows payment comment with variance indication

**Effort estimate**: Small — 2 days. Schema additions + handlers + notification triggers.

### Total Tier 4 #13 backend additions

A80 (4) + A81 (4–5) + A82 (4–5) + A83 (2) = **14–16 days**.

---

## What this surface does NOT cover

- Customer registration / customer accounts — explicitly removed per your direction
- Comment replies from tenant to customer — Phase 2; tenant uses Customer Comms (Tier 1.5) for replies
- Full template editing by tenants — Phase 2; structured customization only in MVP
- Customer dashboard / multi-quote history — Phase 2
- PDF or print-friendly view of public quote/invoice — Phase 2
- Multi-language customer-facing pages — Phase 2
- Custom domain for tenant short links — Phase 2; pilot.tr (or similar) Pilot-managed for MVP
- Stripe Connect for direct-to-tenant payment routing — Phase 2 architectural decision
- Marketing site at pilotfortrades.com — Tom-owned pre-launch hygiene; not in this spec

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A80–A83 added (4 additions). Cumulative through Tier 4 #13: A1–A83.

**Backend day estimate update**:
- Pre-Tier-4-#13 cumulative remaining MVP: 229–298.5 days
- Tier 4 #13 additions: 14–16 days
- New cumulative remaining MVP: **243–314.5 days**

**Framework doc**: Tier 4 #13 status flips from `pending` to `locked`. Tier 4 #14 (help/about/feedback) is the final remaining surface.

**Arch doc touch-up needed at Pass 4 close**: a section on Customer-Facing Public Surfaces covering the signed URL model, Stripe one-time payment integration, email template framework with tenant customization, and short-link infrastructure. Plus the Stripe Connect architectural review flag.

**PRD touch-up needed at Pass 4 close**: §3.7 (Notifications & Comms) extension for the email template framework and customization. §3.10 (Sales & Quoting) extension for customer accept/decline with comment. §3.6 (Invoicing & Billing) extension for Stripe one-time payment + variance handling. New cross-cutting customer-facing-page pattern in §4.

**Pre-launch hygiene track**: 16 email templates' final copy, customer-facing email default copy, "Powered by Pilot" footer copy, marketing site at pilotfortrades.com, short-link domain registration (e.g., `pilot.tr`).

## Next: Tier 4 #14 — Help / About / Feedback Surfaces

Tier 4 #14 is the final Pass 4 surface. Shape A (full flow spec). Hosts:
- In-app help system (contextual help articles, search)
- About / version / legal links surface
- Feedback submission flow with diagnostic data option
- Customer support handoff content (Tom owns content)

Estimated 400–550 lines per the framework's Shape A definition.

After Tier 4 #14 closes, **Pass 4 closes**. Substantial post-Pass-4 work then begins:
- Full v3.1 PRD issued (consolidates all interim updates)
- Full v5 arch doc issued (consolidates v4.1, v4.2, v4.3 patches)
- Full v6 backend ledger issued (cumulative through Pass 4)
- Framework doc gets its third (and final) full rewrite
- Doc consolidation pass per your direction (you'll provide updated docs; I review and add missed content from prior flows)
- Pre-launch hygiene completion check
