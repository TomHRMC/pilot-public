# Design Prompt: UI-FIX-2F — Payment Method Screen + Stripe Connect Flow (UI Designer Phase)

**Mode**: Pilot Web UI Designer  
**Batch**: UI-FIX-2F (Design Phase)  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-020`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2f-design.md`  
**Estimated session**: 2 hours  
**Platform**: Web (`apps/web`) — Settings page within the authed layout  
**Output**: A detailed design spec at `dev-docs/architecture-design/batch-designs/batch-ui-fix-2f-ui-design-spec.md`  
**Next step**: Tom reviews and approves. Python Engineer implements backend, then React Engineer implements frontend.

---

## ⚠️ MANDATORY STOP: Read These First

Before producing any design, read:

- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-2f-design.md`** — all sections A–G. Understand the full technical scope before designing.
- **`dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-020`** — the full FIX-020 section including the Stripe Connect OAuth flow.
- **`dev-docs/architecture-design/batch-designs/ui-fix-1-decisions.md § FIX-004`** — the original payment architecture decision (FIX-004) including the manual payment fallback behavior.

Also read these source files:

```
frontend/apps/web/src/app/(authed)/settings/billing/page.tsx
  ← Current billing page — understand what already exists

frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx
  ← Current billing settings component — see what's already there

frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx
  ← Understand the Settings layout/shell pattern used by other settings pages
```

---

## Background: Why This Matters

This is one of the most important MVP features. Without it:
- Pilot's `create_payment_intent()` currently routes all customer payments through **Pilot's own Stripe account** instead of the tenant's Stripe account — this is incorrect and legally problematic
- Contractors cannot take real card payments from their customers until they connect their Stripe account
- The public invoice payment page shows an empty or broken payment form for disconnected tenants

This batch implements the complete Stripe Connect onboarding experience so contractors can connect their Stripe account and immediately start accepting customer card payments.

---

## Product Context: The Two States

### State 1 — Stripe NOT Connected (default for all new tenants)

The tenant has not yet connected their Stripe account. When customers view their invoice, they see manual payment instructions (phone, email, "pay by check/Zelle"). No card payment is possible.

**What the settings page should show**:
- Clear explanation that connecting Stripe enables online card payments from customers
- Prominent "Connect Stripe Account" button (this is the primary CTA)
- Information about what happens without Stripe (manual payment fallback — not a failure, just a different mode)
- Possibly show a preview of what customers will see on the invoice payment page in each state

### State 2 — Stripe CONNECTED

The tenant's Stripe account is linked. Customers will see a card payment form on the invoice payment page and payments go directly to the contractor's Stripe account (not Pilot's).

**What the settings page should show**:
- ✅ Connected confirmation with the Stripe account name/display
- Option to "Disconnect" (with a warning about what this means for outstanding invoices)
- Last 4 of connected bank account if available

---

## Stripe Account Links Flow (Technical — must be reflected in UX)

Pilot uses **Stripe Account Links** (server-side hosted onboarding) — NOT the legacy OAuth/`ca_` approach. This is simpler and better UX.

**The flow**:

1. Contractor is on the Payment Method settings page
2. They click "Connect Stripe Account"
3. Pilot's backend creates a Stripe Account Link (a time-limited Stripe-hosted URL)
4. The browser is redirected to Stripe's website — a standard Stripe onboarding page
   - If the contractor **already has a Stripe account**: Stripe shows "Connect your existing account to Pilot For Trades"
   - If they **don't have a Stripe account**: Stripe shows a sign-up flow (enter bank account, business info)
5. Contractor completes on Stripe's site
6. Stripe redirects them back to `https://app.pilotfortrades.com/settings/billing/payment-method?connected=true`
7. Pilot shows success state and verifies connection via `GET /status`

**Additional state — Incomplete onboarding (contractor clicked away before finishing)**:
- When they return to the Payment Method page: status shows `connected=true, charges_enabled=false`
- Page shows: "Setup incomplete — click Resume to finish connecting your Stripe account"
- "Resume Setup" button generates a new Account Link for the same Stripe account

**UX implications to design for**:
- The "Connect Stripe Account" button causes a full page navigation away from the app — make this clear ("You'll be redirected to Stripe to connect your account")
- Stripe's site handles both existing-account login and new-account creation — the UX is identical from Pilot's perspective
- After returning with `?connected=true`: show success banner, fetch updated status
- After returning with `?retry=true` (Account Link expired): show "Session expired — click to try again" with a re-connect button
- If onboarding is incomplete (`charges_enabled=false`): show "Resume Setup" state, not a full success state

---

## Design Requirements

### Screen: `/settings/billing/payment-method`

This page lives inside the Settings shell (with `SettingsSidebar` on the left). It is accessible from:
- The Profile dropdown → "Payment Method" (per FIX-019 nav redesign)

The page must have a clear page title and description.

---

### Section 1 — Connection Status Card

A card/panel at the top of the page showing the current Stripe connection status.

**Disconnected state**:
```
┌─────────────────────────────────────────────────────────────┐
│  🔗  Stripe Account                                          │
│                                                              │
│  No Stripe account connected                                 │
│  Connect your Stripe account to accept card payments from    │
│  your customers directly on invoice payment pages.          │
│                                                              │
│  [Connect Stripe Account →]                                  │
│                                                              │
│  ℹ️  Without Stripe, customers will see manual payment       │
│  instructions (phone, email) on their invoices.             │
└─────────────────────────────────────────────────────────────┘
```

**Incomplete onboarding state** (`connected=true` but `charges_enabled=false`):
```
┌─────────────────────────────────────────────────────────────┐
│  ⏳  Stripe Account — Setup Incomplete                       │
│                                                              │
│  Your Stripe account has been created but onboarding        │
│  is not yet complete. Customers cannot pay by card yet.     │
│                                                              │
│  [Resume Setup →]                                            │
└─────────────────────────────────────────────────────────────┘
```

**Connected state** (`charges_enabled=true`):
```
┌─────────────────────────────────────────────────────────────┐
│  ✅  Stripe Account — Connected                              │
│                                                              │
│  Acme Electric LLC (Stripe account)                         │
│  Customers can now pay by card on invoice payment pages.    │
│                                                              │
│  [Disconnect]                                                │
└─────────────────────────────────────────────────────────────┘
```

---

### Section 2 — Manual Payment Fallback Info (always visible)

Below the connection status card, a section explaining the manual payment behavior. This is always visible regardless of Stripe connection status — it's informational.

```
Manual Payment (Always Available)
──────────────────────────────────────────────────────────────
Even without Stripe, customers can pay by:
• Check — mail to your address
• Cash — in person
• Zelle/Venmo — your contact details on the invoice
• Wire transfer

When a payment is received, record it manually in Pilot from
the invoice detail page → "Record Payment".
```

---

### Section 3 — Disconnect Confirmation

When the contractor clicks "Disconnect", show a **confirmation modal** before disconnecting:

```
Disconnect Stripe?

Disconnecting your Stripe account will:
• Prevent new card payments on invoice payment pages
• Customers will see manual payment instructions instead
• Existing recorded payments are not affected

[ Cancel ]  [ Disconnect Stripe ]  (Disconnect button in red/fault)
```

---

### Loading / Error States

**Loading state**: While fetching connection status on page load — show a skeleton/spinner within the status card.

**Error state**: If status fetch fails — show an error message within the status card: "Unable to load payment status. Please refresh the page."

**Connect redirect**: The "Connect Stripe Account" button should show a loading state briefly (spinner inside button) after click before the redirect happens, to indicate something is happening.

**Post-connect success**: When returning from Stripe OAuth with `?connected=true` in the URL — show a success notification or a green banner at the top: "✅ Your Stripe account has been connected. Customers can now pay by card."

**Post-connect error**: When returning with `?error=connect_failed` — show an error: "Could not connect your Stripe account. Please try again or contact support."

---

## Design Token Constraints

ALL colors must use existing `pilotPreset` tokens:

| Use | Token |
|---|---|
| Connected status icon | `text-margin-600` (green) |
| Disconnected/neutral | `text-neutral-500` |
| Connect button | `bg-brand-600 text-white hover:bg-brand-700` |
| Disconnect button | `border border-fault-300 text-fault-700 hover:bg-fault-50` |
| Disconnect confirm button | `bg-fault-600 text-white hover:bg-fault-700` |
| Info box background | `bg-neutral-50 border border-neutral-200` |
| Success banner | `bg-margin-50 border border-margin-200 text-margin-800` |
| Error banner | `bg-fault-50 border border-fault-200 text-fault-800` |
| Loading spinner | `text-brand-600` |
| Card/panel | `bg-white border border-neutral-200 rounded-lg` |

---

## Quality Bar

This page is one the contractor sees when setting up their account before accepting customer payments. It must be:
- **Clear and confidence-inspiring** — the contractor must feel safe connecting their bank account
- **Informative, not alarming** — explain the manual payment fallback positively, not as a failure state
- **Consistent with the Settings shell** — matches the look of other settings pages (Team, Operations, etc.)
- **Actionable** — every state has a clear next action
- **Honest about the OAuth redirect** — don't make the user think a modal will open; they're leaving the page

---

## Output: Design Spec Document

Produce a design spec at:

**`dev-docs/architecture-design/batch-designs/batch-ui-fix-2f-ui-design-spec.md`**

Required sections:

1. **Page Overview** — route, access path (Profile dropdown), user roles who see this (owner only via RBAC)

2. **Connection Status Card — Disconnected State**
   - Exact dimensions, padding, border-radius
   - Icon choice for "not connected" indicator
   - Typography: heading size, body size (token references)
   - CTA button: label, size, token colors
   - Info text styling

3. **Connection Status Card — Connected State**
   - ✅ icon / connected indicator
   - Account display format (name + what details to show)
   - Disconnect button styling and position

4. **Manual Payment Info Section**
   - Layout (bulleted list or card)
   - Typography
   - Whether it's collapsible or always expanded

5. **Disconnect Confirmation Modal**
   - Modal dimensions
   - Content (warning text)
   - Button styling (Cancel = secondary, Disconnect = fault-600)
   - Overlay background

6. **Loading State**
   - Skeleton or spinner for status card during load

7. **Post-Connect Success Banner**
   - Position (top of page, below header)
   - Dismissible or auto-dismiss?
   - Token colors

8. **Post-Connect Error Banner**
   - Same position decisions as success
   - Error message text

9. **Connect Button Loading State**
   - Spinner inside button, button disabled, label change

10. **Transitions/Animations**
    - Any animations between states (e.g., fade-in of success banner)

11. **Component Manifest** — list of every file the React Engineer creates/modifies with file paths

12. **Implementation Notes for React Engineer** — e.g., "check for `?connected=true` and `?error=connect_failed` query params on mount to show success/error banners"

---

After completing the design spec, notify Tom that it is ready for review. Implementation does not start until Tom approves.
