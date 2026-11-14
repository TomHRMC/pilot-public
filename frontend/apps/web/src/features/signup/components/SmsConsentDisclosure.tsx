/**
 * SmsConsentDisclosure — SIGNUP-C "Stay Informed" 10DLC consent disclosure
 *
 * Location: apps/web/src/features/signup/components/SmsConsentDisclosure.tsx
 *
 * This block IS the TCR consent screenshot content for the CXXXXXX campaign
 * resubmission (see telnyx-10dlc-p4t-tenant-comms-campaign.md §5). It renders
 * the full required 10DLC CTA language verbatim and is always visible beneath
 * the consent checkbox (both checked and unchecked states).
 *
 * The exported `SMS_CONSENT_DISCLOSURE_TEXT` constant is the single source of
 * truth for the SHA-256 disclosure hash sent to POST /phone/consent. Any
 * mismatch between the hashed text and the rendered text breaks the TCPA
 * audit trail — never edit one without the other.
 *
 * Token audit (Section H): all colors from pilotPreset tokens — zero hex.
 */

"use client";

import React from "react";
import {
  InformationCircleIcon,
  ArrowTopRightOnSquareIcon,
} from "@heroicons/react/24/outline";

/**
 * The exact disclosure text rendered in the disclosure paragraph.
 *
 * This is the canonical string hashed (SHA-256) and sent as
 * `disclosure_hash` in the POST /phone/consent request. The backend stores
 * it in `user_sms_consent_audit.consent_text_hash` for the TCPA audit trail.
 *
 * Required 10DLC CTA elements (each MUST appear — verified by unit test):
 *  1. Program name "Pilot for Trades"
 *  2. Message types "account, billing & security alerts"
 *  3. "Message frequency varies"
 *  4. "Msg & data rates may apply"
 *  5. "Reply HELP for help, STOP to opt out"
 *  6. Privacy Policy link → https://www.pilotfortrades.com/legal/privacy
 *  7. No-sharing statement
 *
 * NOTE: The Privacy Policy link is rendered as a separate anchor within the
 * paragraph (not part of this raw text constant). The hash is computed over
 * this constant only — the link href is stable and not user-editable, so it
 * does not need to be in the hashed payload.
 */
export const SMS_CONSENT_DISCLOSURE_TEXT =
  "Account & support alerts from Pilot for Trades. You'll receive account, billing, security, and support messages — including replies to support requests you submit to us — at the mobile number provided. Message frequency varies. Msg & data rates may apply. Reply HELP for help, STOP to opt out. See our Privacy Policy. Mobile information will not be shared with third parties or used for marketing purposes.";

const PRIVACY_POLICY_URL = "https://www.pilotfortrades.com/legal/privacy";

/**
 * Splits the disclosure text around "Privacy Policy" so the link can be
 * rendered inline while keeping the hashed constant intact. The split token
 * matches the exact phrase in SMS_CONSENT_DISCLOSURE_TEXT.
 */
const PRIVACY_PHRASE = "See our Privacy Policy.";

export function SmsConsentDisclosure() {
  // Split the canonical text so "Privacy Policy" becomes a clickable link.
  const parts = SMS_CONSENT_DISCLOSURE_TEXT.split(PRIVACY_PHRASE);
  const beforeLink = parts[0] ?? "";
  const afterLink = parts[1] ?? "";

  return (
    <section
      aria-label="SMS consent disclosure"
      data-testid="signup-sms-consent-disclosure"
      className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 flex gap-3 items-start"
    >
      <InformationCircleIcon
        className="w-5 h-5 text-neutral-500 flex-shrink-0"
        aria-hidden="true"
      />
      <p className="text-xs leading-relaxed text-neutral-700 flex-1">
        {beforeLink}
        <a
          href={PRIVACY_POLICY_URL}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Pilot for Trades Privacy Policy (opens in new tab)"
          className="text-brand-600 hover:text-brand-800 underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
        >
          Privacy Policy
          <ArrowTopRightOnSquareIcon
            className="w-3 h-3 inline ml-0.5"
            aria-hidden="true"
          />
        </a>
        {afterLink}
      </p>
    </section>
  );
}
