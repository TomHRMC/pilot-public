# Pilot for Trades Design System — Pass 4, Tier 3 #10 + #11: Onboarding Flow + Mobile Push Permission

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Complete onboarding experience for new tenants — minimum-required signup wizard, post-wizard checklist with optional setup tasks, trial-to-paid conversion flow, mobile push notification permission flow with timing strategy. Largest single Pass 4 spec — covers tenant lifecycle from initial signup through full activation.
**Depends On**: All Pass 1–3 flow specs · Tier 1, 1.5, 2 specs · Settings IA framework · Tier 3 #8 + #9 states catalog (F1–F8 first-time-user states inherit here)
**Backend additions**: A73 (trial state machine + tenant signup), A74 (legal acceptance recording), A75 (subscription tier infrastructure), A76 (Stripe integration for paid conversion), A77 (onboarding state tracking + checklist resumability), A78 (mobile push permission tracking)
**Deliverable shape**: Shape A (Full flow spec) per Pass 4 framework doc — largest single Pass 4 spec because tenant lifecycle has many distinct sub-flows

---

## Purpose

Onboarding is the inverse of every other Pilot surface. Other surfaces assume a tenant exists with users, configuration, and data. Onboarding has to bring those into existence. It bootstraps everything that other surfaces take as a given.

The strategic frame: **get the user to "real Pilot" within minutes**, not hours. The minimum-required wizard handles only what genuinely must happen first (account, legal, optional phone, tier choice). Everything else — catalog setup, customer import, integration connections, team invitations — happens contextually after the wizard via a pinned checklist on the dashboard.

This spec also covers mobile push notification permission, which is a one-shot OS-level decision with high cost if asked badly. Timing matters: ask too early and the user denies without context; ask too late and the user encounters notification gaps that should have been prevented.

Trial-as-tier framing: a trial is just a subscription tier with full features, no price, time-bounded duration. Trial users get an accurate preview of paid Pilot. Conversion to paid is a tier change at Stripe with payment method collection.

## Strategic direction

### Minimum-required wizard, post-wizard checklist hybrid

Five steps in the minimum-required wizard cover what genuinely must happen at signup:
1. Account creation (email, password, name, business info)
2. Legal acceptance (ToS, privacy, EULA)
3. Phone verification (optional — only required if user wants SMS MFA or to receive SMS notifications)
4. Subscription tier selection (Trial selected by default; can pick paid tier with Stripe at this step)
5. Confirmation and routing to dashboard

After the wizard, the user lands on the dashboard with a pinned "Setup checklist" widget covering everything optional: customer setup, catalog setup, integrations, team invitations, etc. The user can engage with the checklist or ignore it. Items dismiss as completed (or are explicitly skipped).

This pattern is standard in modern B2B SaaS for good reason: it gets users to value quickly while preserving guidance for the optional setup that makes the product fully useful.

### Trial-as-tier — full features, no payment, time-bounded

The trial isn't a special mode. It's a subscription tier with these properties:
- Full feature parity with paid tiers (no feature gates during trial)
- $0 price (no Stripe payment required at signup)
- 14- or 30-day duration (configurable per tenant by Pilot operator; default set by operator)
- Inherits Starter tier's user limit so trial users see an accurate Starter experience
- Converts to a paid tier at trial end (or whenever the user chooses earlier)

This framing keeps the implementation clean — no "trial mode vs. paid mode" branching throughout the codebase. Just a subscription tier with the trial flag set.

### Tax setup is the only genuine in-app gate

Per Q3 in our scoping discussion, all configuration except tax setup uses defaults that work without setup. Tax is the exception because Pilot can't generate accurate invoices without tax rates. Approach: tenant can use everything in Pilot immediately (quotes, jobs, customer comms, etc.) without tax setup. The first time they try to convert a quote to an invoice or generate an invoice directly, they hit a contextual "Set up tax rates first" sub-flow. Just-in-time configuration; not a wizard step.

### Phone verification is opt-in for SMS notifications and SMS MFA only

Customer SMS messaging works regardless of the owner's personal phone — it uses the tenant's Telnyx number (Tier 1.5). The owner's personal phone is only needed for *receiving* SMS notifications about Pilot activity (quote approvals, conflicts, customer messages) or for using SMS as an MFA method. Wizard step 3 makes this clear: provide phone if you want SMS notifications or SMS MFA; skip if not.

### Mobile push permission: ask after the user has context

Per Q4 in our scoping, push permission request fires after onboarding's mobile setup step (typically the first time a user installs and opens the mobile app). This gives the user just-in-time context — "your owner just assigned you to a job; want to be notified when there's an update?" If they deny, fall back to email + in-app banner channels per Tier 2 #5; don't re-prompt aggressively.

### Operator admin surface is hidden Pilot routes (not standalone admin app)

Per your direction, per-tenant trial length and other operator-controlled values are managed via hidden Pilot routes accessible only to operator-role users (your account). For MVP, operator-role tenants and per-tenant overrides can be managed via direct DB updates if the hidden routes aren't ready. This spec doesn't design the operator admin UI itself — that's separate operator infrastructure work. Tier 3 #10 specs only what onboarding needs to know about operator-controlled values (trial length, tier configuration).

## Locked design decisions — Onboarding (Tier 3 #10)

### 1. Pre-signup landing — out of scope for this spec

The marketing site landing page where prospective customers learn about Pilot and click "Start free trial" is not part of this spec. Pre-launch hygiene includes the marketing site as separate work owned by Tom. This spec begins at the moment a user clicks "Start free trial" or "Sign up" and lands on Pilot's signup page.

### 2. Wizard step 1 — Account creation

**Decision**: Single page with these fields:

```
┌───────────────────────────────────────────────────────────────────────┐
│ Welcome to Pilot for Trades                                           │
│ ────────────────────────────                                          │
│                                                                       │
│ Step 1 of 5: Create your account                                      │
│                                                                       │
│ Business name *                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │                                                                 │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ Your name *                                                           │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │                                                                 │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ Your email *                                                          │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │                                                                 │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ Password *                                                            │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │                                                                 │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│ Must be 12+ characters with mix of upper, lower, number, symbol.      │
│                                                                       │
│ Trade *                                                               │
│ [▼ Electrical                                            ]            │
│                                                                       │
│ Business size *                                                       │
│ [▼ Solo (just me)                                        ]            │
│                                                                       │
│ ZIP/Postal code *                                                     │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │                                                                 │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│ Used to determine your time zone, area code suggestions, and          │
│ sales tax setup.                                                      │
│                                                                       │
│                                                  [Continue]           │
└───────────────────────────────────────────────────────────────────────┘
```

#### Field details

| Field | Validation | Notes |
| :--- | :--- | :--- |
| Business name | Required, 1–200 chars | Becomes tenant name |
| Your name | Required, 1–100 chars | Becomes owner display name |
| Your email | Required, valid email format, unique | Becomes owner login email; verification email sent |
| Password | Per Tier 2 #7 Decision 3 rules | Stored via Cognito |
| Trade | Required, single-select | Initial options: Electrical, Plumbing, HVAC; "Other" available with free-text. Used for trade-specific defaults (Phase 2). For MVP only Electrical works fully. |
| Business size | Required, single-select | Solo (1), Small (2–5), Medium (6–15), Large (16+). Used for tier recommendation in step 4. |
| ZIP/Postal code | Required, valid format | Determines time zone, suggests Telnyx area code, primes tax setup |

**Email verification**: a verification email is sent immediately. The wizard continues without blocking, but the user sees a banner: "Verify your email at [email]@[domain] — link sent." Email verification gates certain operations (sending customer emails, password reset) but doesn't block onboarding completion.

**Password validation runs server-side** per the existing Cognito policy from Tier 2 #7.

**Save behavior**: explicit "Continue" button. On click, the form posts; if validation fails, errors render inline per Tier 3 #8/#9 Er2 (validation error) treatment. On success, the wizard advances to step 2.

**Rationale**: business size and ZIP up-front gives us the data we need for tier recommendation, time zone, and area code suggestion — saving steps later. Trade is forward-looking for Phase 2 vertical expansion. Email verification is decoupled from wizard completion to avoid blocking on email delivery delays.

### 3. Wizard step 2 — Legal acceptance

**Decision**: Single page with three checkboxes for ToS, Privacy Policy, EULA:

```
┌───────────────────────────────────────────────────────────────────────┐
│ Step 2 of 5: Legal agreements                                         │
│                                                                       │
│ Please review and agree to continue.                                  │
│                                                                       │
│ ☐ I agree to Pilot for Trades Terms of Service       [Read full →]    │
│                                                                       │
│ ☐ I agree to the Privacy Policy                       [Read full →]   │
│                                                                       │
│ ☐ I agree to the End User License Agreement (EULA)    [Read full →]   │
│                                                                       │
│ ☐ I'd like to receive product updates and tips by email (optional)    │
│                                                                       │
│ ───                                                                   │
│                                                                       │
│ By clicking Continue, you confirm that you've read and agreed to      │
│ all three required items above.                                       │
│                                                                       │
│ [← Back]                                              [Continue]      │
└───────────────────────────────────────────────────────────────────────┘
```

The "Continue" button is disabled until all three required boxes are checked. The optional marketing-emails checkbox doesn't affect button state.

Each "Read full →" link opens the relevant document inline (modal overlay) without leaving the wizard. Text is the actual legal copy when ready (per pre-launch hygiene track); for development, placeholder text ("Legal copy pending") is acceptable.

#### Acceptance recording (A74 below)

Each acceptance is captured in `tenant_legal_acceptance` with:
- Timestamp
- IP address
- User-Agent
- Document version hash (so future changes can prompt re-acceptance)
- User identity (the tenant owner being created)

Captures audit-grade legal acceptance proof.

**Rationale**: required-before-continue gate is appropriate for legal agreements. Inline document reading keeps users in the wizard. Marketing-email opt-in is intentionally separate and not required (CAN-SPAM and GDPR best practice).

### 4. Wizard step 3 — Phone verification (optional)

**Decision**: A clear opt-in page with explainer copy:

```
┌───────────────────────────────────────────────────────────────────────┐
│ Step 3 of 5: Phone verification (optional)                            │
│                                                                       │
│ Add your phone if you want to:                                        │
│ • Receive SMS alerts (quote approvals, customer messages, etc.)       │
│ • Use SMS as a way to verify logins (SMS MFA)                         │
│                                                                       │
│ You can use Pilot to text customers regardless — that uses a          │
│ separate Pilot-assigned number.                                       │
│                                                                       │
│ Phone number                                                          │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ +1                                                              │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ [Send verification code]      [Skip for now]                          │
│                                                                       │
│ [← Back]                                                              │
└───────────────────────────────────────────────────────────────────────┘
```

#### "Send verification code" path

Phone number entered → SMS verification code sent to the number → user enters code on next sub-screen → on success, phone is verified and saved to user profile. User then continues to step 4.

If the verification code SMS fails to deliver, the UI shows: "Couldn't deliver code. Try again or skip and add later." User can re-attempt or skip.

#### "Skip for now" path

User clicks Skip → confirmation dialog: "Skip phone verification? You can add a phone later in Settings, but you won't be able to use SMS notifications or SMS MFA until you do." User confirms or returns. On confirm, advances to step 4.

#### Verification flow detail

```
┌───────────────────────────────────────────────────────────────────────┐
│ Enter verification code                                               │
│                                                                       │
│ We sent a 6-digit code to +1-xxx-xxx-1234. Enter it below.            │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │  [_] [_] [_] - [_] [_] [_]                                      │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ Didn't receive a code?  [Resend]   [Use different number]             │
│                                                                       │
│ [← Back]                                              [Verify]        │
└───────────────────────────────────────────────────────────────────────┘
```

After successful verification, brief success state ("✓ Phone verified") and auto-advance to step 4.

**Rationale**: opt-in framing with clear value proposition. The "uses a separate number for customer texting" callout prevents confusion. Resend and "different number" affordances handle the realistic failure modes.

### 5. Wizard step 4 — Subscription tier selection

**Decision**: A page showing all available tiers as cards with Trial pre-selected by default:

```
┌───────────────────────────────────────────────────────────────────────┐
│ Step 4 of 5: Pick your plan                                           │
│                                                                       │
│ Start free for [14] days. Upgrade anytime — no credit card required   │
│ until you do.                                                         │
│                                                                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐          │
│  │ ✓ Trial         │ │ Starter         │ │ Professional    │          │
│  │ Selected        │ │                 │ │                 │          │
│  │                 │ │                 │ │                 │          │
│  │ FREE            │ │ $149/mo         │ │ $249/mo         │          │
│  │ for [14] days   │ │                 │ │                 │          │
│  │                 │ │                 │ │                 │          │
│  │ Up to 5 users   │ │ Up to 5 users   │ │ Up to 15 users  │          │
│  │ Full features   │ │ Full features   │ │ Full features   │          │
│  │                 │ │                 │ │                 │          │
│  │ (current)       │ │ [Select]        │ │ [Select]        │          │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘          │
│                                                                       │
│  ┌─────────────────┐                                                  │
│  │ Enterprise      │                                                  │
│  │                 │                                                  │
│  │ $449/mo         │                                                  │
│  │                 │                                                  │
│  │ Up to 50 users  │                                                  │
│  │ Full features   │                                                  │
│  │                 │                                                  │
│  │ [Select]        │                                                  │
│  └─────────────────┘                                                  │
│                                                                       │
│  Recommended for your business size: Starter                          │
│  Based on your "Solo" answer in step 1.                               │
│                                                                       │
│ [← Back]                                              [Continue]      │
└───────────────────────────────────────────────────────────────────────┘
```

#### Tier cards — content

- **Trial**: "FREE for [N] days" where N is the tenant's effective trial length (default per operator setting; tenant override available per Pilot operator)
- **Starter / Professional / Enterprise**: monthly price (placeholders $149 / $249 / $449), user count limit, full features confirmation

Tier names, prices, and user limits are read from the `subscription_tier` table at render time. Adding new tiers in the future is a DB update, not a code change.

#### Recommended tier highlight

Based on the business size selected in step 1:
- Solo / Small (1–5 users) → Recommended: Starter
- Medium (6–15 users) → Recommended: Professional
- Large (16+ users) → Recommended: Enterprise

The recommended tier card has a subtle "Recommended" badge in addition to the user's selection state.

#### Default selection

Trial is selected by default. User can change to a paid tier at this step if they want to skip the trial — useful for tenants who already know they want Pilot. If user picks a paid tier here, they'll go through Stripe payment in step 5 instead of going to dashboard directly.

#### Trial conversion flow (later)

Users who pick Trial in step 4 can convert to a paid tier at any time during their trial via `Settings > Subscription & Billing > Upgrade plan`. The trial-to-paid conversion is the same payment flow as paying at signup (Stripe payment + tier change).

#### Trial expiration

When the trial ends without conversion, the tenant is auto-downgraded to a "trial expired" state — read-only access to data (no new captures, no SMS, no quote sends, no integration sync) plus a paywall surface requiring payment to resume. Data is preserved through trial expiration.

The paywall surface shows: "Your trial has ended. Pick a plan to continue using Pilot." With the same tier picker UI as step 4 of the wizard, plus Stripe payment.

**Rationale**: card-based mutually-exclusive picker is appropriate for tier selection. Trial-as-default reduces friction at signup. Recommended tier based on business size guides without forcing. Trial expiration with data preservation is the standard pattern that lets dormant trials resurrect easily.

### 6. Wizard step 5 — Confirmation

**Decision**: Last step depends on whether trial or paid was selected in step 4.

#### Trial path

Single-page confirmation summarizing what was set up:

```
┌───────────────────────────────────────────────────────────────────────┐
│ Step 5 of 5: You're all set!                                          │
│                                                                       │
│ ✓ Account created (mike@johnson-electric.example.com)                         │
│ ✓ Legal agreements accepted                                           │
│ ✓ Phone verified (+1-xxx-xxx-1234)                                    │
│ ✓ Trial started — full features for 14 days                           │
│                                                                       │
│ When your trial ends, we'll prompt you to pick a plan. No credit      │
│ card needed until then.                                               │
│                                                                       │
│ Next steps:                                                           │
│ • Add your first customers                                            │
│ • Set up your catalog                                                 │
│ • Connect QuickBooks or Calendar                                      │
│ • Invite your team                                                    │
│                                                                       │
│ All of this can be done from the dashboard — we'll guide you there.   │
│                                                                       │
│                                                  [Get started →]      │
└───────────────────────────────────────────────────────────────────────┘
```

User clicks "Get started →" → routes to `/dashboard` with the post-wizard checklist surface (Decision 7).

#### Paid path

Step 5 becomes the Stripe payment collection step:

```
┌───────────────────────────────────────────────────────────────────────┐
│ Step 5 of 5: Set up payment                                           │
│                                                                       │
│ You picked: [Starter] - $149/month                                    │
│                                                                       │
│ Card information                                                      │
│ [Stripe Elements card input]                                          │
│                                                                       │
│ Billing address                                                       │
│ [Stripe Elements address input]                                       │
│                                                                       │
│ ┌──────────────────────────────────────────────────────────────────┐  │
│ │ Today's charge: $149.00                                          │  │
│ │ Then $149/month, cancel anytime.                                 │  │
│ │                                                                  │  │
│ │ Billing email: mike@johnson-electric.example.com                         │  │
│ └──────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│ [← Back]                                              [Pay $149]      │
└───────────────────────────────────────────────────────────────────────┘
```

Stripe Elements handles the card collection (PCI-compliant, no card details touch Pilot servers). On successful payment, brief loading state, then routes to `/dashboard` with the post-wizard checklist surface.

If payment fails (declined, insufficient funds, etc.), Er2 (validation) treatment per Tier 3 #8/#9: Stripe error message renders inline; user can retry or change card.

**Rationale**: trial path summarizes and motivates next steps; paid path handles payment securely via Stripe. Both paths converge to the same post-wizard checklist.

### 7. Post-wizard dashboard with pinned checklist

**Decision**: After wizard completion, user lands on the standard dashboard (per Pass 2 §5) with a pinned "Setup checklist" widget at the top of the customizable widget grid.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Dashboard                                                               │
│ ──────────                                                              │
│                                                                         │
│ Welcome to Pilot, Mike!                                                 │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────┐    │
│ │ Setup checklist (3 of 8 done)                          [Hide]   │    │
│ │ ───────────────                                                 │    │
│ │                                                                 │    │
│ │ ✓ Create your account                                           │    │
│ │ ✓ Accept legal agreements                                       │    │
│ │ ✓ Pick a plan                                                   │    │
│ │ ─                                                               │    │
│ │ ☐ Add your first customer            [Add now]                  │    │
│ │ ☐ Set up your catalog                [Set up]                   │    │
│ │ ☐ Connect QuickBooks                 [Connect]   [Skip]         │    │
│ │ ☐ Connect your calendar              [Connect]   [Skip]         │    │
│ │ ☐ Invite your team                   [Invite]    [Skip]         │    │
│ │                                                                 │    │
│ │ You can come back to this anytime from your dashboard.          │    │
│ └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│ [Other dashboard widgets here]                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Checklist items

Eight items total, three already complete (the wizard steps 1, 2, 4):

| Item | Action | Done when |
| :--- | :--- | :--- |
| Create your account | (auto-completed during wizard) | User completed step 1 |
| Accept legal agreements | (auto-completed during wizard) | User completed step 2 |
| Pick a plan | (auto-completed during wizard) | User completed step 4 |
| Add your first customer | Routes to Customers > New customer | First customer created |
| Set up your catalog | Routes to Settings > Catalog & Pricing | First catalog item added |
| Connect QuickBooks | Opens QuickBooks OAuth flow | OAuth completed |
| Connect your calendar | Opens Calendar OAuth flow | OAuth completed |
| Invite your team | Routes to Settings > Users & Roles > Invite | First invite sent |

#### Item states

- **Done** (✓): green checkmark; item collapses to single line
- **Not done, primary action available**: ☐ + "[Action button]" + (sometimes) "[Skip]" link
- **Skipped**: shown with strikethrough + "(skipped — [Re-enable])" link to bring it back

#### Skip behavior

Each skippable item has a "Skip" link beside the action button. Clicking skip dismisses the item with confirmation: "Skip 'Connect QuickBooks'? You can connect it anytime from Settings." Skip persists across sessions.

#### Hide behavior

The "[Hide]" button at the top of the widget collapses the entire checklist to a compact pill: "Setup checklist (3 of 8 done) · [Show]". Hide persists across sessions. The pill remains until checklist is fully complete or hidden permanently via "Don't show again" option.

#### Auto-completion detection

When the user completes a checklist item via any path (not just clicking the action in the widget), the item auto-marks as done. For example, if Mike adds his first customer via voice command rather than clicking "Add now" in the widget, the customer creation event triggers checklist progress.

#### Persistence

Checklist state is per-tenant (not per-user). Once an item is complete, every user in the tenant sees it as complete.

**Rationale**: pinned widget is prominent without blocking. Users can engage at their own pace. Auto-completion detection prevents the "I already did this elsewhere; why is it still nagging me?" frustration. Hide and skip affordances respect user agency.

### 8. Mobile setup phase — first mobile login

**Decision**: When the owner (or any tenant user) logs into mobile for the first time, a brief mobile setup phase fires before they reach the standard mobile UI.

```
┌──────────────────────────────────────┐
│ Welcome to Pilot mobile, Mike!       │
│ ──────────                           │
│                                      │
│ A few quick things to set up.        │
│                                      │
└──────────────────────────────────────┘

[Tap to continue]

┌──────────────────────────────────────┐
│ Permission: Notifications            │
│ ──────────                           │
│                                      │
│ Pilot uses push notifications to     │
│ alert you when:                      │
│                                      │
│ • A customer texts you back          │
│ • You're assigned a new job          │
│ • A quote needs your approval        │
│ • Your sync needs attention          │
│                                      │
│ Without push, you'll still get       │
│ email and in-app alerts.             │
│                                      │
│ [Allow notifications] [Maybe later]  │
└──────────────────────────────────────┘
```

#### Push permission request flow

When the user taps "Allow notifications," the OS-level permission prompt fires (iOS or Android system dialog). On grant, push token is registered (per A51); a brief confirmation appears.

When the user taps "Maybe later," the screen advances without firing the OS prompt. They can grant later via settings.

When the OS prompt itself is denied (after Allow notifications was tapped), the screen shows: "No worries — you'll get email and in-app alerts. You can change this anytime in Settings."

This is Tier 3 #11's central design (more detail below in the dedicated #11 section).

#### Mobile setup steps after permission

After push permission resolution, brief tutorial cards walk through:

1. **The Today tab** — "This is your home base. See your schedule, customer messages, and inbox."
2. **The voice mic** — "Tap the mic anywhere to use voice. Try 'show me today' to see your schedule."
3. **Quick wins** — "You're all set! Tap the mic and try a voice command, or browse the app."

After step 3, user reaches the standard mobile UI (Today tab).

#### Skip-everything affordance

A small "Skip tutorial" link in the upper right of each tutorial card lets the user skip ahead. They land on the Today tab immediately.

**Rationale**: mobile setup is a one-time experience that gives users the mental model for voice-first usage. Push permission is asked here with context. Tutorial is brief — users in the field don't have time for long onboarding.

### 9. Tax setup contextual sub-flow

**Decision**: When a user attempts to convert a quote to an invoice or generate an invoice directly without tax rates configured, they hit a contextual "Set up tax rates first" sub-flow:

```
┌───────────────────────────────────────────────────────────────────────┐
│ Set up tax rates first                                                │
│                                                                       │
│ Pilot needs tax rates configured before you can generate invoices.    │
│ This takes about 2 minutes.                                           │
│                                                                       │
│ Your tax jurisdiction (auto-detected from your business address)      │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ California, USA                                                 │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│ Default sales tax rate                                                │
│ ┌────────┐                                                            │
│ │ 7.25 % │                                                            │
│ └────────┘                                                            │
│ This is the standard rate for your area. You can override per         │
│ customer or per job line item.                                        │
│                                                                       │
│ Tax-exempt customers handling                                         │
│ ☐ Some of my customers are tax-exempt                                 │
│   (We'll show a tax-exempt toggle on customer records)                │
│                                                                       │
│ [← Cancel] [Save and generate invoice]                                │
└───────────────────────────────────────────────────────────────────────┘
```

#### Sub-flow behavior

- The sub-flow is modal-feeling — it appears over the user's current context (the quote-to-invoice conversion)
- Auto-detected tax jurisdiction comes from the ZIP/postal code in step 1; user can override
- Default rate is suggested based on jurisdiction (state-level or country-level rate); user can change
- Tax-exempt toggle is a tenant-wide flag — when on, customer records show a tax-exempt checkbox
- On save, user's invoice generation continues
- Subsequent invoices use the saved tax setup; sub-flow only fires once

#### Setting placement

Tax setup lives at `Settings > Tax configuration` (per Pass 2 §3.12 placement) for ongoing edits. The contextual sub-flow is a one-time priming experience.

**Rationale**: just-in-time configuration matches user mental model (they only think about tax when generating invoices). Auto-detection reduces friction. Tax-exempt is opt-in to keep the UI simple for tenants without tax-exempt customers.

### 10. Trial expiration UX

**Decision**: When a trial expires, the tenant enters a "trial expired" state with read-only access and a paywall:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Your trial has ended                                                    │
│ ──────────────────                                                      │
│                                                                         │
│ Pick a plan to keep using Pilot. Your data is preserved — pick up       │
│ right where you left off.                                               │
│                                                                         │
│ [Tier picker UI — same as wizard step 4]                                │
│                                                                         │
│                                              [Pick a plan]              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Read-only access during expired state

- All existing data visible (customers, jobs, quotes, invoices, etc.)
- New data creation blocked (Er3 modal: "Trial expired — pick a plan to continue")
- SMS sending blocked
- Voice intents available but limited to read-only operations ("show me today" works; "create quote" fails with paywall prompt)
- Mobile app shows the same paywall on launch

#### Pre-expiration warnings

Email + push notifications fire at:
- 7 days before expiration: "Your trial ends in 7 days. Upgrade to keep using Pilot."
- 3 days before: same message, more urgent
- 1 day before: same, final notice
- On expiration day: "Your trial has ended. Pick a plan to continue."

In-app banner appears starting 7 days before expiration. Banner is dismissable but reappears on next session until user upgrades or trial ends.

#### Conversion at trial end

User clicks "Pick a plan" → tier picker UI (same component as wizard step 4) → Stripe payment → tenant resumes normal operation.

**Rationale**: read-only with paywall is the standard pattern that lets dormant trials convert easily without losing data. Pre-expiration warnings give users time to evaluate and decide. Paywall surface uses the same tier picker as wizard for consistency.

### 11. Onboarding state tracking and resumability

**Decision**: Onboarding state is stored per-tenant; user can leave the wizard mid-flow and resume on next login.

#### Wizard state model

| Wizard step | State stored |
| :--- | :--- |
| Step 1 (account creation) | Once submitted, account is created in Cognito; cannot resume "before" |
| Step 2 (legal acceptance) | Each accept saves immediately; resume picks up at next unaccepted item |
| Step 3 (phone verification) | If Skip clicked, marked skipped; if verified, saved; if started but not completed, prompts to resume on next login |
| Step 4 (tier selection) | Trial selected by default if user lands at this step; if user starts paid flow but abandons, marks tier as "selecting" and resumes here |
| Step 5 (confirmation/payment) | If trial: auto-completed when reached; if paid: payment failure resumes here on next login |

#### Resume behavior

If a user logs in and onboarding wizard is incomplete:
- Routes them to wherever they left off in the wizard
- Wizard header shows: "Welcome back, Mike. Let's pick up where you left off."
- Pre-filled fields where state is known
- User can navigate back through completed steps to review/edit

#### Checklist resumability

Checklist items persist across sessions and across users in the tenant. Adding a customer via the checklist or via voice is detected by both paths; checklist updates accordingly.

**Rationale**: real users abandon mid-flow. Resumability prevents lost signups. Pre-filling reduces friction. Auto-detection of checklist completion via any path keeps the checklist accurate.

## Locked design decisions — Mobile push permission (Tier 3 #11)

### 12. Push permission request timing — after onboarding mobile setup

**Decision**: Push permission request fires on the second screen of mobile setup (the Permission: Notifications screen in Decision 8 above). Not on first app launch (no context); not deep into product use (timing unpredictable).

Specifically:
- User completes desktop signup wizard
- User installs and opens the mobile app
- User logs in (using credentials created during desktop signup)
- Mobile setup phase begins automatically
- After "Welcome to Pilot mobile" intro screen, the Permission: Notifications screen appears
- Push permission request fires when user taps "Allow notifications"

Per Q4 in our scoping, this gives users just-in-time context.

### 13. Push permission request copy and presentation

**Decision**: A pre-permission "explainer screen" appears before the OS-level permission dialog. This is critical because once the OS dialog is dismissed (especially on iOS), it's hard to ask again.

```
┌──────────────────────────────────────┐
│ 🔔 Permission: Notifications         │
│ ──────────                           │
│                                      │
│ Pilot uses push notifications        │
│ to alert you when:                   │
│                                      │
│ • A customer texts you back          │
│ • You're assigned a new job          │
│ • A quote needs your approval        │
│ • Your sync needs attention          │
│                                      │
│ Without push, you'll still get       │
│ email and in-app alerts when you     │
│ open Pilot.                          │
│                                      │
│ ┌───────────────────────────────┐    │
│ │ Allow notifications            │   │
│ └───────────────────────────────┘    │
│ ┌───────────────────────────────┐    │
│ │ Maybe later                    │   │
│ └───────────────────────────────┘    │
└──────────────────────────────────────┘
```

#### "Allow notifications" path

User taps Allow → OS-level permission prompt fires → on grant, push token registered via A51, success state shown briefly, screen advances. On deny, fall-back state shown (see below).

#### "Maybe later" path

User taps Maybe later → screen advances without firing OS prompt. Tracked in `mobile_push_permission_state` as `not_asked` (per A78 below). User can grant later via Settings > Notifications.

### 14. Push permission denial UX

**Decision**: When the user denies push permission (either at the OS prompt or by tapping Maybe later), Pilot accepts gracefully:

- Brief acknowledgment: "No worries — you'll get email and in-app alerts. You can change this anytime in Settings."
- Mobile setup continues normally
- Notification preferences (Tier 2 #5) automatically default with push set to OFF and email + in-app banner enabled
- No re-prompt aggression — the user's choice is respected
- A small banner on the Today tab shows: "📱 Push is off. [Turn on for instant alerts]" (dismissable; reappears once after a week if dismissed; does not reappear after second dismissal)

### 15. Push permission state persistence

**Decision**: Mobile push permission state is tracked per-device in `mobile_push_permission_state`:

- `not_asked` — user hasn't been asked yet (rare; most users hit the request on first mobile login)
- `granted` — user granted push permission and token is registered
- `denied_by_user_choice` — user tapped Maybe later
- `denied_by_os` — user tapped Allow but OS prompt was denied
- `revoked_in_settings` — user previously granted but later turned off in OS settings

State is read on every mobile app launch to determine whether to show the dismissable banner (Decision 14). State changes (e.g., user enables push later in Settings) trigger re-registration of push token.

### 16. Phase 2 — time windows for push notifications

**Per your direction**: time windows for push notifications (e.g., "no push between 10 PM and 6 AM") is Phase 2.

For MVP, push notifications fire whenever a notification is generated. Quiet hours are explicitly out of scope.

Phase 2 should include:
- Per-user quiet hours configuration (in `Mobile > Settings > Notifications > Quiet hours`)
- Server-side enforcement (notifications generated during quiet hours are queued and delivered when quiet hours end)
- Override for critical notifications (Field issues forced-minimum push from Tier 2 #5 ignores quiet hours)

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| Minimum-required wizard + post-wizard checklist hybrid | **NEW** | — |
| Trial-as-tier framing (no separate "trial mode" branching) | **NEW** | — |
| Auto-completion detection for checklist items | **NEW** | — |
| Just-in-time configuration (tax sub-flow) | **NEW** | — |
| Pre-permission explainer screen before OS prompt | **NEW** | — |
| Graceful denial fallback for OS-level permissions | **NEW** | — |
| Trial expiration with read-only fallback + paywall | **NEW** | — |
| Resumable wizard state | **NEW** | — |
| Tier card picker for subscription selection | **NEW** | Tier 2 #6 card pattern (extended from preview-and-pick to select-and-buy) |
| Stripe Elements for PCI-compliant payment | **NEW** | — |
| Operator-controlled per-tenant settings (trial length) | **NEW** | — |
| Three-tier resolution chain (operator → tenant → user) | Reused | A53 (Tier 2 #4) — operator-level extension to existing tenant + user override |
| First-time-user state hooks integrated with checklist | Reused | Tier 3 #8/#9 (F1–F8) — the same surfaces serve onboarding-checklist-target and empty-state purposes |

## Cross-domain considerations

### A. Pre-launch hygiene integration

Per Pass 4 framework, several pre-launch hygiene items are hosted by Tier 3 #10:
- ToS, Privacy Policy, EULA copy → reserved slots in step 2; Tom owns content
- Welcome email template visual + copy → email sent on signup completion; Tom owns content
- Marketing site / pre-signup landing → adjacent ops work; not in this spec

Tier 3 #10 reserves the surfaces; legal review fills in the content. Wizard is functional with placeholder copy during development.

### B. Tier 2 #5 notification preferences integration

When a user completes onboarding without granting push permission (Decision 14), their notification preferences (Tier 2 #5) automatically default with push OFF and email + in-app banner ON. This produces a sensible default that doesn't require the user to revisit notification settings.

When the user later grants push permission (via Settings > Notifications or by enabling in OS settings), their preferences automatically update to enable push for default categories. The user can customize further per Tier 2 #5.

### C. First-time-user states (Tier 3 #8/#9) are the destination for checklist actions

Each checklist item routes the user to a surface that, on first arrival, shows the corresponding F1–F8 first-time-user state from Tier 3 #8/#9. The first-time-user state's CTA performs the same action as the checklist item. So users who navigate via the checklist or via the navigation menu both land on the same welcoming experience.

### D. Pilot operator admin surface — separate work

Per your direction (operator-controlled values managed via hidden Pilot routes), this spec doesn't design the operator admin UI itself. The data model includes operator-controlled settings (`system_default_trial_length_days`, `tenant_trial_length_days_override`), and the spec calls out that operator admin work is separate from Pass 4 design. For MVP, direct DB updates are acceptable until the hidden routes are built.

This includes:
- Per-tenant trial length override
- Per-tenant subscription tier override (force a tier without payment for special cases)
- Tenant suspension/restoration
- Tenant deletion / data purge

All operator-admin surfaces. Out of scope for Tier 3 #10. Flagged here for awareness.

### E. Stripe integration architecture

Stripe is the payment processor for MVP. Integration scope:

- **Stripe Elements** for card collection at signup and trial conversion
- **Stripe Subscriptions** for recurring billing
- **Stripe Webhooks** for billing events (subscription updated, payment failed, payment succeeded, subscription canceled)
- **Customer Portal** for self-service tier changes / payment method updates / cancellation (Phase 2 feature; MVP has Settings > Subscription & Billing surface)

A76 below covers the Stripe integration scope. Critical: Pilot never sees raw card details; Stripe Elements handles PCI compliance natively.

### F. Email verification integration

Account email verification is decoupled from wizard completion to avoid blocking on email delivery. However, several actions require verified email:
- Sending customer emails (Flow 4 — verified email is sender domain context)
- Password reset (verified email is recovery channel)
- Subscription tier downgrade requiring confirmation

If user attempts these without verified email, an Er2 (validation error) state surfaces with "Verify your email first" CTA → resends verification email and shows status.

### G. Subscription billing UX

Settings > Subscription & Billing (Pass 2 §3.11; designed by Tier 2 #4 indirectly) has these features added by Tier 3 #10:

- Current tier display with usage stats (users, SMS segments — only what's tracked per Q-Usage)
- "Upgrade plan" affordance opening tier picker
- "Manage payment method" via Stripe Customer Portal (Phase 2; MVP has read-only display)
- "Cancel subscription" with retention prompt and data preservation behavior
- Invoice history (read-only list of past Stripe invoices)
- "Apply for tax-exempt status" (Phase 2)

### H. Trial detection across the codebase

Multiple surfaces need to know "is this tenant on a trial?" Centralized in:
- `subscription_tier.is_trial` (boolean column in tier table; the trial tier has this true)
- `tenant.current_subscription_tier_id` references the active tier

Code paths that gate behavior on trial state (e.g., trial expiration paywall, trial-end notifications) read these columns. Backend pattern: trial state is a query, not a separate code path.

### I. Mobile checklist visibility

The post-wizard checklist (Decision 7) is web-only in MVP. Mobile users see a simpler version: a single banner on the Today tab that says "Complete your setup on the web — [N] tasks remaining" with a link that opens the web dashboard. Tablet (web in Field Mode) shows the standard web checklist.

Phase 2 may add a full mobile checklist if observed user demand justifies. For MVP, the web is the right surface for setup tasks because most checklist items (catalog setup, integrations, team invites) are web-primary anyway.

### J. Tax setup detection

Detection of "tenant doesn't have tax rates configured" runs on every quote-to-invoice conversion attempt and on every direct invoice creation attempt. Server-side check; if tax setup is incomplete, returns 412 (precondition required) with structured payload that frontend uses to render the contextual sub-flow.

## Deferred items (Phase 2 / for future iteration)

- **Push notification time windows / quiet hours** — Phase 2 per your direction
- **Self-service tier upgrades via Stripe Customer Portal** — Phase 2; MVP has the wizard tier picker
- **Trial extensions** — owner requests "give me one more week" — Phase 2 (operator can do via DB for MVP)
- **Family/multi-tenant accounts** — one user managing multiple tenants — Phase 2
- **Tenant deletion / data purge self-service** — Phase 2; operator-handled in MVP
- **SSO at signup** — Phase 2; password-only signup in MVP
- **Onboarding tour with coach marks** — Phase 2; current welcome screens are minimal
- **Trade-specific defaults** (different defaults for plumbing vs electrical) — Phase 2 with vertical expansion
- **Multi-language onboarding** — Phase 2 with multi-language UI
- **Onboarding A/B testing** for activation optimization — Phase 2 with analytics infrastructure
- **Push permission re-prompt strategies** — Phase 2 (user research on what works without feeling pushy)
- **Feature-tier differentiation** — Phase 2 (MVP differentiates only by user count)
- **Usage-based pricing per category** — Phase 2 (MVP tracks users + SMS only)
- **Tenant data export at trial expiration** — Phase 2 (current model preserves data within Pilot for resurrection)
- **Custom onboarding paths per business size** — Phase 2 (MVP recommends a tier but uses same checklist for all)

## Validation checklist

Before implementation begins:

- [ ] Wizard step 1 fields and validation rules confirmed
- [ ] Email verification decoupled from wizard completion per Decision 2
- [ ] Legal documents (ToS, Privacy, EULA) version hashing implemented per Decision 3 / A74
- [ ] Phone verification opt-in flow tested per Decision 4
- [ ] Tier picker reads from `subscription_tier` table per Decision 5 / A75
- [ ] Trial expiration with read-only fallback + paywall implemented per Decision 10
- [ ] Stripe Elements integration tested at wizard step 5 (paid path) per Decision 6 / A76
- [ ] Post-wizard checklist with auto-completion detection per Decision 7 / A77
- [ ] Mobile setup phase with push permission request timing per Decisions 8, 12
- [ ] Pre-permission explainer screen before OS prompt per Decision 13
- [ ] Push permission denial graceful fallback per Decision 14
- [ ] Push permission state tracking per Decision 15 / A78
- [ ] Tax setup contextual sub-flow per Decision 9
- [ ] Resumable wizard state per Decision 11
- [ ] Trial-as-tier framing implemented (no separate "trial mode" branching) per Strategic Direction
- [ ] Operator admin surface deferred to separate work per Strategic Direction
- [ ] Pre-launch hygiene reservations confirmed (legal copy, email templates) per Cross-Domain A
- [ ] Push notification time windows explicitly Phase 2 per Decision 16

## Backend additions (new for Tier 3 #10 + #11)

### A73. Trial State Machine + Tenant Signup

**Triggered by**: Decisions 2, 5, 10, 11 — trial-as-tier framing, tenant signup, trial expiration, wizard resumability.

**Scope**:

**Schema**:
- New table `tenant_signup`
  - `tenant_id` UUID PK
  - `signup_state` TEXT (`step1_account | step2_legal | step3_phone | step4_tier | step5_confirm | complete`)
  - `signup_started_at` TIMESTAMPTZ
  - `signup_completed_at` TIMESTAMPTZ NULL
  - `business_name`, `trade`, `business_size`, `zip`, `time_zone` — collected during step 1
- Tenant table extended with:
  - `current_subscription_tier_id` FK → subscription_tier
  - `trial_started_at` TIMESTAMPTZ NULL
  - `trial_ends_at` TIMESTAMPTZ NULL
  - `trial_length_days_override` INTEGER NULL — set by operator if differs from system default
  - `stripe_customer_id` TEXT NULL — populated on first paid conversion

**Services**:
- `services/tenant_signup.py` — handles the wizard state machine
- `services/trial_management.py` — handles trial expiration, paywall enforcement, conversion

**Trial expiration enforcement**:
- New Celery task `enforce_trial_expirations` runs hourly
- For tenants where `trial_ends_at <= now()` and tier is still trial, transitions to `trial_expired` state
- Sends paywall notification (push + email + in-app banner)

**APIs**:
- `POST /api/v1/signup` — initiate signup; creates tenant in `step1_account` state
- `PUT /api/v1/signup/{tenant_id}/step{N}` — advance the wizard one step at a time
- `GET /api/v1/signup/{tenant_id}/state` — get current signup state for resumability

**Effort estimate**: Medium-Large — 5–6 days. Schema + state machine + trial expiration enforcement + APIs + Celery tasks.

### A74. Legal Acceptance Recording

**Triggered by**: Decision 3 — legal acceptance during wizard step 2.

**Scope**:
- New table `tenant_legal_acceptance`
  - `acceptance_id` UUID PK
  - `tenant_id` UUID FK
  - `user_id` UUID FK — the user who accepted (the owner during signup)
  - `document_type` TEXT (`tos | privacy | eula | marketing_email_optin`)
  - `document_version_hash` TEXT — hash of the document text version accepted
  - `accepted_at` TIMESTAMPTZ
  - `ip_address` INET
  - `user_agent` TEXT
- Per (tenant_id, user_id, document_type) — multiple rows allowed if document version changes and user re-accepts
- API: `POST /api/v1/signup/{tenant_id}/legal/accept` — record acceptance; called per checkbox check
- API: `GET /api/v1/signup/{tenant_id}/legal/required` — returns list of legal documents that need acceptance (fresh on signup; only previously-unaccepted-versions on subsequent re-acceptance flows)

**Document version hashing**: each legal document has a version hash computed from its content. Hash changes when document content changes. Tenants whose accepted hash differs from current are prompted to re-accept on next login.

**Phase 2**: re-acceptance flow when documents change. MVP: documents are versioned but re-acceptance is a separate flow not in MVP scope.

**Effort estimate**: Small — 2 days. Schema + recording API + version hashing.

### A75. Subscription Tier Infrastructure

**Triggered by**: Decision 5 — tier selection, trial-as-tier framing.

**Scope**:
- New table `subscription_tier`
  - `tier_id` UUID PK
  - `tier_name` TEXT (`trial | starter | professional | enterprise | ...`)
  - `display_label` TEXT — user-facing label
  - `monthly_price_cents` INTEGER NOT NULL — `0` for trial
  - `is_trial` BOOLEAN — true only for the trial tier
  - `trial_duration_days` INTEGER NULL — set for trial tier; system default
  - `max_users` INTEGER NOT NULL — user count limit
  - `max_sms_segments_per_month` INTEGER NULL — null = unlimited; otherwise enforced (overage billing per Tier 1.5)
  - `is_active` BOOLEAN — true if available for new signups
  - `display_order` INTEGER — order in tier picker UI
- Seed data: Trial, Starter, Professional, Enterprise per Decision 5 placeholder values
- Frontend reads from this table at render time; tier names/prices/limits flexible via DB updates

**Operator-controlled overrides**:
- New table `tenant_tier_override`
  - `tenant_id` UUID PK
  - `override_tier_id` UUID FK → subscription_tier — if set, supersedes normal tier
  - `override_trial_length_days` INTEGER NULL — if set, supersedes system default
  - `override_reason` TEXT NULL — operator note
  - `set_by_operator_user_id` UUID
- Read by tenant signup flow and trial expiration flow

**Usage tracking**:
- New table `tenant_subscription_usage`
  - `tenant_id` UUID
  - `period_start`, `period_end` TIMESTAMPTZ — aligned to subscription billing cycle
  - `current_user_count` INTEGER
  - `current_sms_segment_count` INTEGER (links to A65 from Tier 1.5)
- Updated by user-add events and SMS-send events

**APIs**:
- `GET /api/v1/subscription-tiers` — returns active tiers for tier picker
- `GET /api/v1/tenants/{tenant_id}/subscription` — returns current tier + usage stats
- `PUT /api/v1/tenants/{tenant_id}/subscription/upgrade` — initiate tier change (calls into A76 for Stripe)

**Tier limit enforcement**:
- User-add flow checks `current_user_count >= max_users`; if so, returns Er3-class error with "Upgrade tier" CTA
- SMS-send flow checks `current_sms_segment_count >= max_sms_segments_per_month`; per Tier 1.5 quota model

**Effort estimate**: Medium — 4 days. Schema + tier picker API + usage tracking + limit enforcement.

### A76. Stripe Integration for Paid Conversion

**Triggered by**: Decisions 5, 6 — Stripe payment for paid tier selection.

**Scope**:

**Stripe Elements integration**:
- Frontend uses Stripe Elements (card input + address input)
- Backend creates Stripe Customer record on tenant signup with paid tier (or first conversion)
- Backend creates Stripe Subscription with the selected tier's price ID
- On successful subscription creation, tenant tier is updated to the paid tier and trial is converted

**Stripe Webhooks**:
- New endpoint `POST /api/v1/webhooks/stripe` — receives Stripe webhook payloads with signature verification
- Handles events:
  - `customer.subscription.created` — confirm tier activation
  - `customer.subscription.updated` — handle tier changes
  - `invoice.paid` — confirm successful payment
  - `invoice.payment_failed` — trigger payment retry / paywall
  - `customer.subscription.deleted` — handle cancellation
- Stripe webhook signing secret stored in environment

**Tier conversion APIs**:
- `POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial` — initiates conversion; expects Stripe Payment Method ID from frontend Stripe Elements
- `POST /api/v1/tenants/{tenant_id}/subscription/change-tier` — changes between paid tiers (Phase 2 surface; backend supports)

**Payment failure handling**:
- On Stripe payment failure during signup wizard step 5, return Er2 (validation error) state
- For ongoing subscription payment failures, Stripe handles retries (3 attempts over 7 days); after exhaustion, tenant moves to "payment failed" state with paywall

**Phase 2**:
- Stripe Customer Portal for self-service payment method updates
- Annual billing discount
- Coupon / promo code support

**Effort estimate**: Medium-Large — 5–6 days. Stripe Elements integration + Subscriptions API + webhooks + payment failure handling. Stripe API integration is the cost driver.

### A77. Onboarding State Tracking + Checklist Resumability

**Triggered by**: Decisions 7, 11 — checklist persistence + auto-completion + wizard resumability.

**Scope**:

**Checklist state**:
- New table `tenant_onboarding_checklist`
  - `tenant_id` UUID PK
  - `account_created` BOOLEAN — auto-set on signup completion
  - `legal_accepted` BOOLEAN — auto-set on legal acceptance
  - `tier_selected` BOOLEAN — auto-set on tier selection
  - `first_customer_added` BOOLEAN — auto-set on first customer create
  - `first_customer_added_at` TIMESTAMPTZ
  - `catalog_setup` BOOLEAN — auto-set on first catalog item added
  - `catalog_setup_at` TIMESTAMPTZ
  - `quickbooks_connected` BOOLEAN — auto-set on QB OAuth complete
  - `quickbooks_skipped` BOOLEAN — set when user clicks Skip in checklist
  - `calendar_connected` BOOLEAN — auto-set on Calendar OAuth complete
  - `calendar_skipped` BOOLEAN — set when user clicks Skip in checklist
  - `team_invited` BOOLEAN — auto-set on first team invite sent
  - `team_skipped` BOOLEAN — set when user clicks Skip in checklist
  - `checklist_hidden` BOOLEAN — set when user clicks "Hide" in widget
  - `checklist_dismissed_permanently` BOOLEAN — set when user clicks "Don't show again"

**Auto-completion detection**:
- Customer create event → check tenant onboarding state; if `first_customer_added` not yet set, mark true
- Catalog item create event → similar
- QB OAuth complete event → similar
- Calendar OAuth complete event → similar
- Team invite send event → similar
- Each detection runs on the existing event/action handlers in those domains

**APIs**:
- `GET /api/v1/tenants/{tenant_id}/onboarding/checklist` — returns checklist state for widget rendering
- `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/skip/{item}` — mark an item as skipped
- `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden` — toggle widget visibility
- `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/dismissed` — permanent dismiss

**Effort estimate**: Small-Medium — 3 days. Schema + auto-completion event handlers + APIs + widget state management.

### A78. Mobile Push Permission Tracking + Degraded-Mode Fallback

**Triggered by**: Decisions 12, 13, 14, 15 — push permission flow.

**Scope**:

**Schema**:
- New table `mobile_push_permission_state`
  - `tenant_id` UUID
  - `user_id` UUID
  - `device_id` UUID — references A51 push token registry
  - `permission_state` TEXT (`not_asked | granted | denied_by_user_choice | denied_by_os | revoked_in_settings`)
  - `last_state_change_at` TIMESTAMPTZ
  - `dismissable_banner_dismissed_at` TIMESTAMPTZ NULL — for the "push is off" banner reappearance logic

**Mobile app integration**:
- Mobile app reads `permission_state` on launch
- If `permission_state = not_asked` and onboarding is complete, mobile app starts the mobile setup phase (per Decision 8) including the push permission request screen
- If `permission_state = granted`, push token registered via A51
- If `permission_state = denied_*`, dismissable banner shows on Today tab per Decision 14

**APIs**:
- `PUT /api/v1/users/me/devices/{device_id}/push-permission` — update permission state from mobile app
- `GET /api/v1/users/me/devices/{device_id}/push-permission` — get current state (used on app launch)

**Banner reappearance logic**:
- Banner shows on Today tab when `permission_state` is denied
- User can dismiss the banner; recorded in `dismissable_banner_dismissed_at`
- Banner reappears once after 7 days from dismissal
- After second dismissal, banner doesn't reappear

**Effort estimate**: Small — 2 days. Schema + APIs + mobile app state coordination.

### Total Tier 3 #10 + #11 backend additions

A73 (5–6) + A74 (2) + A75 (4) + A76 (5–6) + A77 (3) + A78 (2) = **21–23 days**.

This is the largest single backend addition cluster in Pass 4 because tenant lifecycle infrastructure is genuinely substantial. Stripe integration alone is meaningful work; A73 + A75 + A76 together build the full subscription billing infrastructure.

---

## What this surface does NOT cover

- Pilot operator admin UI for setting per-tenant trial lengths and tier overrides — separate operator infrastructure work; manageable via DB updates for MVP per your direction
- Marketing site / pre-signup landing page — Tom-owned pre-launch hygiene
- Customer Portal for self-service billing management — Phase 2 (uses Stripe's Customer Portal then)
- Tenant data export self-service before trial expiration — Phase 2; uses A71 (Tier 2 #7) flow
- SSO signup integration — Phase 2
- Onboarding tour with coach marks — Phase 2
- Per-trade default configuration (Plumbing, HVAC defaults) — Phase 2 with vertical expansion
- Trial-extension self-service — Phase 2; operator-handled via DB for MVP
- Push permission time windows / quiet hours — Phase 2 per Decision 16
- Re-acceptance flow when legal documents change — Phase 2
- Annual billing tier discount — Phase 2

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A73–A78 added (6 additions). Cumulative through Tier 3 #10 + #11: A1–A78.

**Backend day estimate update**:
- Pre-Tier-3-#10/#11 cumulative remaining MVP: 206–273.5 days
- Tier 3 #10 + #11 additions: 21–23 days
- New cumulative remaining MVP: **227–296.5 days**

**Tier 3 closes here.** All Tier 3 surfaces locked: #8 (states catalog), #9 (first-time-user states), #10 (onboarding), #11 (mobile push permission).

**Framework doc**: Tier 3 status flips from `in progress` to `complete`. Tier 4 (#12, #13, #14) becomes the next phase.

**Arch doc touch-up needed at Pass 4 close**: a new chapter §18 SMS Subscription & Onboarding Architecture or extension to existing §3.11 (Subscriptions & Usage) covering the trial-as-tier model, tenant signup state machine, Stripe integration, and operator-controlled overrides. Should also reference the legal acceptance recording (A74) and email verification decoupling.

**PRD touch-up needed at Pass 4 close**: §3.11 (Subscriptions & Usage) needs new feature rows for tier picker, trial-as-tier framing, trial expiration with paywall + data preservation, Stripe integration, and operator-controlled trial length. Plus a new "Onboarding" feature scope in §3.5 (Identity, Access, Tenant) covering the wizard + checklist + resumability + auto-completion detection.

## Next: Tier 4 Polish + Pre-Launch Hygiene

Tier 4 begins. Three surfaces:

- **#12 Flow 3 dispatch board sync indicator amber-with-count refinement** — Shape D incremental addendum to existing Flow 3 spec
- **#13 Customer-facing public quote/invoice link styling pass** — Shape E visual design + content composition; hosts pre-launch hygiene email templates and privacy footer
- **#14 Help / about / feedback surfaces** — Shape A full flow spec; hosts customer support handoff content

Tier 4 is the smallest tier in design effort. After Tier 4 closes, Pass 4 closes; full v3.1 PRD, v5 arch doc, v6 backend ledger get issued; framework doc gets its third (and final-of-MVP) full rewrite.
