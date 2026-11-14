# Pilot for Trades — Partner Submission Materials

> **Correction (2026-11-14):** the Google Calendar description below says no calendar data is stored beyond the sync session. As built, the sync log and conflict tables keep event snapshots (`calendar_sync_log.payload_snapshot`, `calendar_sync_conflict.base_snapshot`) for conflict resolution and audit.

> This document consolidates all brand assets and text fields required for integration partner directory listings, app store submissions, and 10DLC brand registration. Complete one section at a time. All logo files are in `/public/brand/`.

---

## Company Information (shared across all partners)

| Field                     | Value                                                     |
| ------------------------- | --------------------------------------------------------- |
| **Legal company name**    | Example Holdings, LLC           |
| **DBA / Brand name**      | Pilot for Trades                                          |
| **Website URL**           | https://pilotfortrades.com                                |
| **Support email**         | info@pilotfortrades.com                                   |
| **Privacy policy URL**    | https://pilotfortrades.com/legal/privacy                  |
| **Terms of service URL**  | https://pilotfortrades.com/legal/terms                    |
| **Primary brand color**   | `#3b43d6`                                                 |
| **Secondary brand color** | `#181d66`                                                 |
| **Business category**     | Field Service Management / Business Application           |
| **Industry vertical**     | Electrical, Plumbing, HVAC contractors (Specialty Trades) |

---

## Partner 1: QuickBooks / Intuit

**Submission context:** App Marketplace listing (Intuit Developer Portal)

### Required Assets

| Asset             | Spec            | File to use                                                          |
| ----------------- | --------------- | -------------------------------------------------------------------- |
| App icon          | 512×512 PNG     | `logo-icon.svg` → export 512×512 PNG, `#3b43d6` background, no alpha |
| Logo on white     | 1024px wide PNG | `logo-primary.svg` → export on white background, 1024×230            |
| Brand color hex   | string          | `#3b43d6`                                                            |
| Short description | max 100 chars   | See below                                                            |

**Short description (98 chars):**

> AI voice quoting, dispatch board, invoicing & QuickBooks sync for electrical contractors.

**Long description (for marketplace listing, ~300 words):**

> Pilot for Trades is an AI-first field operations platform built for solo and small-crew electrical contractors. Instead of building quotes in spreadsheets at 9 PM, Pilot lets you dictate a job scope by voice on-site — and receive a complete estimate with real-time material pricing, your markup applied, and a professional PDF ready to send.
>
> **QuickBooks Integration:** Pilot connects to QuickBooks Online with two-way, automatic sync. Customers, invoices, and payments stay in sync across both systems with built-in conflict resolution — no duplicate entries, no mystery data. When a customer or invoice changes on both sides, Pilot shows you exactly what changed and lets you pick the correct version.
>
> **What's included:** Voice AI quoting (NEC-aware for electrical work), GPS clock-in/clock-out, real-time job profitability tracking, smart dispatch board, customer SMS, Google Calendar sync, offline mobile app (iOS + Android), Stripe payments, and unlimited users.
>
> **Pricing:** Starter plan at $49/month · Teams plan at $149/month · 14-day free trial, no credit card required.

**OAuth Consent Screen app name:** Pilot for Trades
**OAuth Scopes requested:** `com.intuit.quickbooks.accounting`

---

## Partner 2: Google (Calendar API + OAuth Consent Screen)

**Submission context:** Google Calendar API app registration; Google OAuth consent screen verification

### Required Assets

| Asset              | Spec        | File to use                                            |
| ------------------ | ----------- | ------------------------------------------------------ |
| App icon           | 512×512 PNG | `logo-icon.svg` → export 512×512 PNG, white background |
| App name           | string      | `Pilot for Trades`                                     |
| Privacy policy URL | URL         | `https://pilotfortrades.com/legal/privacy`             |
| Homepage URL       | URL         | `https://pilotfortrades.com`                           |

**OAuth Consent Screen fields:**

| Field                   | Value                                    |
| ----------------------- | ---------------------------------------- |
| App name                | Pilot for Trades                         |
| User support email      | info@pilotfortrades.com                  |
| Developer contact email | info@pilotfortrades.com                  |
| App domain              | pilotfortrades.com                       |
| Privacy policy          | https://pilotfortrades.com/legal/privacy |
| Terms of service        | https://pilotfortrades.com/legal/terms   |

**Scopes requested:**

- `https://www.googleapis.com/auth/calendar.events` — Read and write calendar events (job scheduling)
- `https://www.googleapis.com/auth/calendar.readonly` — Read existing calendar for conflict detection

**Justification text (for Google review):**

> Pilot for Trades uses Google Calendar to sync job appointments and dispatch schedules. Contractors create jobs in Pilot and they appear on their Google Calendar. Calendar read access is used to detect scheduling conflicts before confirming appointments. No calendar data is stored beyond the sync session.

---

## Partner 3: Stripe

**Submission context:** Stripe Connect platform registration; Stripe Dashboard branding

### Required Assets

| Asset                   | Spec                           | File to use                                   |
| ----------------------- | ------------------------------ | --------------------------------------------- |
| Logo (Stripe Dashboard) | PNG on white, preferred square | `logo-primary.svg` → export on white, 512×115 |
| Brand color hex         | string                         | `#3b43d6`                                     |
| Business name           | string                         | `Pilot for Trades`                            |
| Website URL             | URL                            | `https://pilotfortrades.com`                  |

**Stripe Connect Platform fields:**

| Field                | Value                                                                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Platform name        | Pilot for Trades                                                                                                               |
| Business URL         | https://pilotfortrades.com                                                                                                     |
| Support URL          | https://pilotfortrades.com/contact                                                                                             |
| Privacy URL          | https://pilotfortrades.com/legal/privacy                                                                                       |
| Terms URL            | https://pilotfortrades.com/legal/terms                                                                                         |
| Redirect URIs        | `https://pilotfortrades.com/api/v1/stripe/callback`                                                                            |
| Platform description | AI-powered field operations software for electrical contractors. Collects invoice payments on behalf of contractor businesses. |

**Statement descriptor:** PILOT FOR TRADES
**Short descriptor:** P4TRADES

---

## Partner 4: Telnyx — 10DLC Brand Registration (TCR)

**Submission context:** The Campaign Registry (TCR) 10DLC brand registration for SMS sending

### Required Assets

| Asset        | Spec                 | File to use                                                |
| ------------ | -------------------- | ---------------------------------------------------------- |
| Company logo | PNG, minimum 200×200 | `logo-icon.svg` → export 512×512 PNG, `#3b43d6` background |
| Brand name   | string               | See below                                                  |
| Website URL  | URL                  | `https://pilotfortrades.com`                               |
| Vertical     | dropdown             | See below                                                  |

**TCR Brand Registration fields:**

| Field              | Value                                                                                                                                              |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Legal company name | Example Holdings, LLC                                                                                                    |
| Brand display name | Pilot for Trades                                                                                                                                   |
| EIN / Tax ID       | _(insert company EIN)_                                                                                                                             |
| Brand website      | https://pilotfortrades.com                                                                                                                         |
| Business type      | Private Company                                                                                                                                    |
| Vertical           | Small Business                                                                                                                                     |
| Stock symbol       | N/A (private)                                                                                                                                      |
| Brand description  | Software platform providing AI voice quoting, job dispatch, invoicing, and customer communications for electrical, plumbing, and HVAC contractors. |

**TCR Campaign Registration fields:**

| Field                | Value                                                                                                                                                                                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Campaign description | Appointment reminders, on-my-way notifications, and invoice delivery sent to customers of electrical and trades contractors using the Pilot for Trades platform. Messages are sent on behalf of the contractor, not Pilot for Trades directly. |
| Use case             | Mixed (appointment reminders + transactional)                                                                                                                                                                                                  |
| Opt-in method        | Customer provides phone number when booking a service appointment with a Pilot for Trades contractor. SMS terms visible at https://pilotfortrades.com/legal/sms-terms                                                                          |
| Opt-out keywords     | STOP, UNSUBSCRIBE, CANCEL, END, QUIT                                                                                                                                                                                                           |
| Help keywords        | HELP, INFO                                                                                                                                                                                                                                     |
| Sample message 1     | `[Contractor Name] has confirmed your appointment for [Date] at [Time]. Reply STOP to opt out. - Pilot for Trades`                                                                                                                             |
| Sample message 2     | `[Contractor Name] is on the way. Estimated arrival: [Time]. Reply STOP to opt out. - Pilot for Trades`                                                                                                                                        |

---

## Partner 5: Apple App Store

**Submission context:** iOS app submission (App Store Connect)

### Required Assets

| Asset    | Spec                                                                        | File to use                                                                |
| -------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| App icon | 1024×1024 PNG, NO alpha channel, NO rounded corners (Apple applies corners) | `logo-icon.svg` → export 1024×1024 PNG, `#3b43d6` background, remove alpha |

> **Critical:** Apple rejects icons with rounded corners baked in or any alpha transparency. The icon file must be a flat 1024×1024 PNG. Apple's system applies the rounded squircle shape automatically.

**App Store Connect fields:**

| Field              | Value                                    |
| ------------------ | ---------------------------------------- |
| App name           | Pilot for Trades                         |
| Subtitle           | AI Quoting for Contractors               |
| Bundle ID          | com.pilotfortrades.app                   |
| Primary category   | Business                                 |
| Secondary category | Productivity                             |
| Age rating         | 4+                                       |
| Privacy policy URL | https://pilotfortrades.com/legal/privacy |
| Support URL        | https://pilotfortrades.com/contact       |
| Marketing URL      | https://pilotfortrades.com               |

**App Store description (short, 170 chars max):**

> AI voice quoting, dispatch board, invoicing & job profitability for solo electricians and small trade crews. Works offline.

**App Store keywords (100 chars max):**

> electrical,quoting,contractor,invoice,dispatch,voice AI,QuickBooks,field service,trades,electrician

---

## Partner 6: Google Play Store

**Submission context:** Android app submission (Google Play Console)

### Required Assets

| Asset           | Spec                          | File to use                                                              |
| --------------- | ----------------------------- | ------------------------------------------------------------------------ |
| App icon        | 512×512 PNG, NO alpha channel | `logo-icon.svg` → export 512×512 PNG, `#3b43d6` background, remove alpha |
| Feature graphic | 1024×500 PNG                  | See design spec below                                                    |

**Feature Graphic (1024×500) design spec:**

- Background: brand gradient `#3b43d6` → `#181d66` (135deg)
- Left side: `logo-primary-dark.svg` centered vertically, ~300px wide
- Right side: tagline text "Master the Craft. Automate the Rest." in white, 32px Inter 700
- Bottom-right: small "Available for Android" pill badge, white outline

**Google Play Console fields:**

| Field             | Value                                                                             |
| ----------------- | --------------------------------------------------------------------------------- |
| App name          | Pilot for Trades                                                                  |
| Short description | AI voice quoting, dispatch & invoicing for electrical contractors. Works offline. |
| Category          | Business                                                                          |
| Tags              | field service, contractor, electrical, quoting, invoicing                         |
| Email (support)   | info@pilotfortrades.com                                                           |
| Phone (support)   | _(insert support phone if available)_                                             |
| Website           | https://pilotfortrades.com                                                        |
| Privacy policy    | https://pilotfortrades.com/legal/privacy                                          |

**Full description (max 4000 chars):**

> **Pilot for Trades — AI Field Operations for Electrical Contractors**
>
> Stop building quotes on spreadsheets at 9 PM. Pilot is the AI-first platform that handles everything between your first call and the final invoice.
>
> **Voice AI Quoting**
> Describe the job in plain trade language. Pilot builds the estimate — materials at today's prices, labor at your rates, your markup applied — in under 60 seconds. Works on-site, in the truck, or between jobs. NEC-aware for electrical scopes.
>
> **Real-Time Job Profitability**
> Track costs against the quoted price as the job happens, not three weeks later. See your margin on every job, every day, from your phone.
>
> **Smart Dispatch Board**
> Your whole week at a glance. Drag to reschedule, detect conflicts before they become callbacks, route techs with drive-time estimates.
>
> **Customer Communications**
> Automated appointment reminders, on-my-way texts, and invoice notifications — all previewed before they send.
>
> **QuickBooks Online Sync**
> Two-way automatic sync with built-in conflict resolution. Customers, invoices, and payments stay in sync.
>
> **Offline-First Mobile**
> Works in basements, rural service calls, and dead zones. Data syncs when you're back in signal.
>
> **What's included:**
>
> - Voice AI quoting (NEC-aware)
> - iOS + Android, works offline
> - GPS clock-in/clock-out + photo docs
> - Real-time job profitability (ETC)
> - Dispatch board with conflict detection
> - Customer quotes, invoicing, Stripe payments
> - QuickBooks Online sync
> - Google Calendar sync
> - Customer SMS + appointment reminders
> - Unlimited users, unlimited jobs
>
> **14-day free trial. No credit card required.**
> Starter: $49/month · Teams: $149/month
