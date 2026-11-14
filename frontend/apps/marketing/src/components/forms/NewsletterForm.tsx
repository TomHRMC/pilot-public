/**
 * NewsletterForm — NEW for MKT-B1.5
 *
 * Email field + optional trade_interest checkboxes.
 * Extends <TurnstileProtectedForm> for shared Turnstile + honeypot security.
 * POSTs to POST /api/v1/marketing/newsletter.
 *
 * Designed for footer + blog post inline use — compact layout.
 */

"use client";

import { useState } from "react";
import TurnstileProtectedForm, {
  useTurnstileProtection,
  SubmitSpinner,
  FormErrorAlert,
} from "./TurnstileProtectedForm";

// ---------------------------------------------------------------------------
// UTM helper — provides defaults for organic traffic
// ---------------------------------------------------------------------------

function getUtmParams(): {
  utm_source: string;
  utm_medium: string;
  utm_campaign: string | null;
} {
  if (typeof window === "undefined") {
    return { utm_source: "website", utm_medium: "organic", utm_campaign: null };
  }
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get("utm_source") ?? "website",
    utm_medium: params.get("utm_medium") ?? "organic",
    utm_campaign: params.get("utm_campaign") ?? null,
  };
}

// Requires 2+ char TLD — catches me@me.t which browser type="email" allows
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface NewsletterFormProps {
  /** Where the form is rendered — passed as `source` to the API */
  source?: string;
  /** Controls whether the trade checkboxes are shown (default: true) */
  showTradeInterest?: boolean;
  /** Dark theme — for use on dark backgrounds like the footer */
  dark?: boolean;
}

// ---------------------------------------------------------------------------
// Trade interest options (matches §6.6 schema)
// ---------------------------------------------------------------------------

const TRADE_OPTIONS = [
  { value: "electrical", label: "⚡ Electrical" },
  { value: "plumbing", label: "💧 Plumbing" },
  { value: "hvac", label: "❄️ HVAC" },
  { value: "all", label: "All trades" },
] as const;

// ---------------------------------------------------------------------------
// Inner fields — has access to TurnstileContext
// ---------------------------------------------------------------------------

function NewsletterFields({
  source,
  showTradeInterest,
  dark,
  isReady,
}: NewsletterFormProps & { isReady: boolean }) {
  const { turnstileToken, honeypot } = useTurnstileProtection();
  const [email, setEmail] = useState("");
  const [tradeInterest, setTradeInterest] = useState<string[]>([]);
  const [status, setStatus] = useState<
    "idle" | "submitting" | "success" | "error"
  >("idle");
  const [errorMsg, setErrorMsg] = useState("");

  function toggleTrade(value: string) {
    setTradeInterest((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!email.trim()) {
      setErrorMsg("Please enter your email address.");
      setStatus("error");
      return;
    }
    if (!EMAIL_REGEX.test(email.trim())) {
      setErrorMsg(
        "Please enter a valid email address (e.g. name@example.com).",
      );
      setStatus("error");
      return;
    }
    if (!turnstileToken) {
      setErrorMsg("Please wait for the security check to complete.");
      setStatus("error");
      return;
    }

    setStatus("submitting");
    setErrorMsg("");

    const { utm_source, utm_medium, utm_campaign } = getUtmParams();

    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/v1/marketing/newsletter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          trade_interest: tradeInterest.length > 0 ? tradeInterest : null,
          source: source ?? "footer",
          utm_source,
          utm_medium,
          utm_campaign,
          cf_turnstile_response: turnstileToken,
          honeypot,
        }),
      });

      if (res.status === 201 || res.ok) {
        setStatus("success");
      } else {
        const data = await res.json().catch(() => ({}));
        // FastAPI 422 returns detail as an array of validation error objects —
        // never a plain string. Normalize before storing in state.
        const detail = data?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((err: { msg: string }) => err.msg).join(", ")
              : "Something went wrong. Please try again.";
        setErrorMsg(msg);
        setStatus("error");
      }
    } catch {
      setErrorMsg("Unable to connect. Please try again.");
      setStatus("error");
    }
  }

  const mutedColor = dark ? "var(--neutral-400)" : "var(--neutral-500)";

  if (status === "success") {
    return (
      <div
        className="rounded-lg px-4 py-3 text-sm font-medium"
        style={{
          background: dark ? "var(--margin-400-15)" : "var(--margin-50)",
          border: `var(--divider-thin) solid ${dark ? "var(--margin-400-30)" : "var(--margin-400)"}`,
          color: dark ? "var(--margin-400)" : "var(--margin-600)",
        }}
        role="status"
        aria-live="polite"
      >
        ✓ You&apos;re subscribed! We&apos;ll send you trade tips and product
        updates.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Email input + submit — horizontal on wide screens */}
      <div className="flex gap-2">
        <div className="flex-1">
          <label htmlFor="nl-email" className="sr-only">
            Enter your email
          </label>
          <input
            id="nl-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{
              background: dark ? "var(--neutral-800)" : "var(--white)",
              border: `var(--divider-thin) solid ${dark ? "var(--neutral-700)" : "var(--neutral-200)"}`,
              color: dark ? "var(--white)" : "var(--neutral-900)",
              outline: "none",
            }}
            autoComplete="email"
          />
        </div>
        <button
          type="submit"
          disabled={status === "submitting" || !isReady}
          className="px-4 py-2 rounded-lg text-sm font-semibold whitespace-nowrap"
          style={{
            background: "var(--brand-600)",
            color: "var(--white)",
            opacity: !isReady ? 0.7 : 1,
          }}
          aria-busy={status === "submitting"}
          onClick={handleSubmit as never}
        >
          {status === "submitting" ? (
            <span className="flex items-center gap-1.5">
              <SubmitSpinner />
              <span>...</span>
            </span>
          ) : (
            "Subscribe"
          )}
        </button>
      </div>

      {/* Trade interest checkboxes (optional) */}
      {showTradeInterest && (
        <fieldset>
          <legend
            className="text-xs font-medium mb-2"
            style={{ color: mutedColor }}
          >
            I&apos;m interested in (optional):
          </legend>
          <div className="flex flex-wrap gap-2">
            {TRADE_OPTIONS.map((t) => {
              const checked = tradeInterest.includes(t.value);
              return (
                <label key={t.value} className="cursor-pointer">
                  <input
                    type="checkbox"
                    value={t.value}
                    checked={checked}
                    onChange={() => toggleTrade(t.value)}
                    className="sr-only"
                  />
                  <span
                    className="inline-block px-3 py-1 rounded-full text-xs font-medium border transition-all"
                    style={{
                      background: checked ? "var(--brand-600)" : "transparent",
                      color: checked ? "var(--white)" : mutedColor,
                      borderColor: checked
                        ? "var(--brand-600)"
                        : dark
                          ? "var(--neutral-600)"
                          : "var(--neutral-200)",
                    }}
                  >
                    {t.label}
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>
      )}

      {status === "error" && errorMsg && <FormErrorAlert message={errorMsg} />}

      <p className="text-xs" style={{ color: mutedColor }}>
        No spam. Unsubscribe anytime.{" "}
        <a
          href="/legal/privacy"
          className="underline"
          style={{ color: dark ? "var(--neutral-400)" : "var(--brand-600)" }}
        >
          Privacy policy
        </a>
        .
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public export
// ---------------------------------------------------------------------------

export default function NewsletterForm({
  source = "footer",
  showTradeInterest = true,
  dark = false,
}: NewsletterFormProps) {
  return (
    <TurnstileProtectedForm
      ariaLabel="Newsletter signup"
      onSubmit={(e) => e.preventDefault()}
    >
      {({ isReady }) => (
        <NewsletterFields
          source={source}
          showTradeInterest={showTradeInterest}
          dark={dark}
          isReady={isReady}
        />
      )}
    </TurnstileProtectedForm>
  );
}
