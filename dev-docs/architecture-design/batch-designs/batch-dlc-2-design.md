# Batch DLC-2 Design — 10DLC MFA Screen Compliance (Web + Mobile)

**Batch code**: DLC-2  
**Date**: 2026-07-24  
**Architect**: Pilot Architect  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P1 — 10DLC Compliance Engineering  
**Telnyx campaign doc**: `dev-docs/integrations/telnyx/telnyx-10dlc-mfa-campaign.md`  
**Status**: READY FOR IMPLEMENTATION  
**Engineer**: React Engineer only (pure frontend — no backend changes)

---

## A. Input Read Summary

| Input | File | Key Finding |
|---|---|---|
| Web MFA page | `apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` | `"use client"` page, renders enrolled methods summary + "Add this method" button + `MFAEnrollmentWizard`. **No privacy policy link present.** |
| Mobile MFA screen | `apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` | Has `disclosureBox` with `testID="sms-disclosure"`. Current text covers consent and data rates but **missing STOP, HELP, frequency, and privacy policy reference** |
| Mobile integration test | `apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx` | Has test asserting `"Message and data rates may apply"` — must be updated to `"Msg & data rates may apply"` to match new wording |
| Telnyx failure reason | Campaign `CYYYYYY` failure code 806 | "Update with specific path for mobile opt-in, HELP instructions, STOP instructions, message frequency disclosure, 'message and data rates may apply' disclosure and link to the message program privacy policy" |
| Telnyx support response | Support feedback (paraphrased) | The opt-in web page needed a privacy-policy link, and the app screenshot needed HELP, STOP, frequency and privacy language. |
| React engr standard inclusions | `frontend/react-engr-std-prompt-inclusions.md` | Read in full — all mandatory sections included in the prompt |

---

## B. Migration Plan

**No database migrations required.** This batch is entirely UI text/link changes.

---

## C. Execution Order

| # | Step | File | Type |
|---|---|---|---|
| 1 | Add compliance footer with privacy policy link | `apps/web/.../security/mfa/page.tsx` | Modify |
| 2 | Replace mobile disclosure text | `apps/mobile/.../security/mfa.tsx` | Modify |
| 3 | Update mobile test text assertion | `apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx` | Modify |
| 4 | Create web disclosure unit test | `apps/web/.../security/mfa/__tests__/MfaMethodsPage.disclosure.test.tsx` | Create |

---

## D. New API Endpoints

None. This batch makes no backend changes.

---

## E. Pattern Reuse Decisions

- No `mvp-arch.md §16` patterns apply — this is compliance text surgery only.
- The existing `disclosureBox` / `disclosureText` StyleSheet pattern from the mobile `mfa.tsx` file is reused as-is. Only the string content changes.
- The web page uses the existing Tailwind `text-xs text-neutral-500` class pattern consistent with other helper-text elements on settings pages.

---

## F. Shared Module Interfaces

None. No shared modules are modified.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Should the web privacy policy link open in a new tab? | Yes — `target="_blank" rel="noopener noreferrer"`. The user is mid-enrollment; opening in same tab would break the flow. |
| Should the mobile privacy policy be a tappable `Linking.openURL` link? | No for this pass. Plain text URL is sufficient for 10DLC screenshot compliance. Tappable link is a P3 UX improvement. |
| What exact frequency wording does Telnyx require? | Standard CTIA form: "Msg freq: 1 message per login or enrollment event." — matches what was submitted in the campaign description. |
| Should the web disclosure be conditional (only shown when SMS is selected)? | No — it must be always visible at CTA level per Telnyx requirement 806. The screenshot must show the disclosure present when the "Add this method" button is visible. |
| Are there other screens that need updating? | No — only the opt-in CTA screens are in scope. The login `MfaChallengeStep` does not display opt-in language and is not reviewed for 10DLC compliance. |

---

## H. Surface Mockup Reference

### Web — `/settings/my-account/security/mfa` (After DLC-2)

```
┌─────────────────────────────────────────────────────┐
│  Two-factor authentication                           │
│  Add an extra layer of security to your account.    │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  No authentication methods enrolled.         │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  By adding an SMS method, you consent to receive    │  ← NEW (always visible)
│  one-time verification codes from Pilot for Trades. │
│  Msg freq: 1 message per login or enrollment event. │
│  Msg & data rates may apply. Reply STOP to opt out. │
│  Reply HELP for help. Privacy policy: [link] ←──── │  ← clickable
│                                                     │
│  [Add this method]                                  │
└─────────────────────────────────────────────────────┘
```

**Screenshot URL for Telnyx**: `https://pilotfortrades.com/compliance/account-add-mfa.png`  
**Settings path**: Settings → My Account → Security → Two-Factor Authentication

### Mobile — Settings → My Account → Security → Two-Factor Authentication (After DLC-2)

```
┌─────────────────────────────────────┐
│  Add an extra layer of security...  │
│                                     │
│  ┌──────────────────────────────┐   │
│  │  No methods enrolled.        │   │
│  └──────────────────────────────┘   │
│                                     │
│  [Add authentication method]        │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ 📱 SMS verification — By     │   │
│  │ enrolling your phone number, │   │
│  │ you agree to receive one-time│   │
│  │ verification codes from      │   │
│  │ Pilot for Trades. Msg freq:  │   │
│  │ 1 message per login or       │   │
│  │ enrollment event. Msg & data │   │
│  │ rates may apply. Reply STOP  │   │
│  │ to opt out. Reply HELP for   │   │
│  │ help. Privacy policy:        │   │
│  │ pilotfortrades.com/legal/    │   │  ← NEW wording
│  │ privacy                      │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Screenshot URL for Telnyx**: `https://pilotfortrades.com/compliance/account-add-mfa-mobile.png`  
**Settings path**: Settings → My Account → Security → Two-Factor Authentication → Add Authentication Method

---

## I. Component Manifest

No new components. Modified files only:

| File | Exists | Action |
|---|---|---|
| `apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` | ✅ | Modify — add compliance paragraph |
| `apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` | ✅ | Modify — update disclosure text |
| `apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx` | ✅ | Modify — update text assertions |
| `apps/web/src/app/(authed)/settings/my-account/security/mfa/__tests__/MfaMethodsPage.disclosure.test.tsx` | ❌ New | Create — 5 compliance assertions |
