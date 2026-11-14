/**
 * CharterApplicationForm — REFACTORED for MKT-B1.5, updated MKT-B6, MKT-B9, C-B1
 *
 * C-B1 changes:
 *   - Renamed from WaitlistForm → CharterApplicationForm
 *   - source default: "charter_page"
 *   - Success copy: "We'll email you when Charter opens"
 *   - Button label: "Be one of the first twelve"
 *
 * MKT-B6 changes:
 *   - name field added (required)
 *   - Client-side validation: trim, email regex, required dropdowns
 *
 * MKT-B9 changes:
 *   - state dropdown added (required — 50 US states + DC + PR + "Outside the US")
 *   - notes textarea added (optional)
 *   - validateCharterApplication updated to require state
 *   - submit body updated to include state + notes
 */

"use client";

import { useState, useRef, useEffect } from "react";
import TurnstileProtectedForm, {
  useTurnstileProtection,
  SubmitSpinner,
  FormErrorAlert,
} from "./TurnstileProtectedForm";

// ---------------------------------------------------------------------------
// US States constant
// ---------------------------------------------------------------------------

const US_STATES = [
  { value: "AL", label: "Alabama" },
  { value: "AK", label: "Alaska" },
  { value: "AZ", label: "Arizona" },
  { value: "AR", label: "Arkansas" },
  { value: "CA", label: "California" },
  { value: "CO", label: "Colorado" },
  { value: "CT", label: "Connecticut" },
  { value: "DE", label: "Delaware" },
  { value: "DC", label: "District of Columbia" },
  { value: "FL", label: "Florida" },
  { value: "GA", label: "Georgia" },
  { value: "HI", label: "Hawaii" },
  { value: "ID", label: "Idaho" },
  { value: "IL", label: "Illinois" },
  { value: "IN", label: "Indiana" },
  { value: "IA", label: "Iowa" },
  { value: "KS", label: "Kansas" },
  { value: "KY", label: "Kentucky" },
  { value: "LA", label: "Louisiana" },
  { value: "ME", label: "Maine" },
  { value: "MD", label: "Maryland" },
  { value: "MA", label: "Massachusetts" },
  { value: "MI", label: "Michigan" },
  { value: "MN", label: "Minnesota" },
  { value: "MS", label: "Mississippi" },
  { value: "MO", label: "Missouri" },
  { value: "MT", label: "Montana" },
  { value: "NE", label: "Nebraska" },
  { value: "NV", label: "Nevada" },
  { value: "NH", label: "New Hampshire" },
  { value: "NJ", label: "New Jersey" },
  { value: "NM", label: "New Mexico" },
  { value: "NY", label: "New York" },
  { value: "NC", label: "North Carolina" },
  { value: "ND", label: "North Dakota" },
  { value: "OH", label: "Ohio" },
  { value: "OK", label: "Oklahoma" },
  { value: "OR", label: "Oregon" },
  { value: "PA", label: "Pennsylvania" },
  { value: "PR", label: "Puerto Rico" },
  { value: "RI", label: "Rhode Island" },
  { value: "SC", label: "South Carolina" },
  { value: "SD", label: "South Dakota" },
  { value: "TN", label: "Tennessee" },
  { value: "TX", label: "Texas" },
  { value: "UT", label: "Utah" },
  { value: "VT", label: "Vermont" },
  { value: "VA", label: "Virginia" },
  { value: "WA", label: "Washington" },
  { value: "WV", label: "West Virginia" },
  { value: "WI", label: "Wisconsin" },
  { value: "WY", label: "Wyoming" },
  { value: "Outside the US", label: "Outside the US" },
];

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

// Requires 2+ char TLD — catches me@me.t which browser type="email" allows
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function validateCharterApplication(
  name: string,
  email: string,
  trade: string,
  companySize: string,
  state: string,
): string | null {
  if (!name.trim()) return "Please enter your name.";
  if (!email.trim()) return "Please enter your email address.";
  if (!EMAIL_REGEX.test(email.trim()))
    return "Please enter a valid email address.";
  if (!trade) return "Please select your trade.";
  if (!companySize) return "Please select your team size.";
  if (!state) return "Please select your location.";
  return null;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CharterApplicationFormProps {
  source?: string;
}

// ---------------------------------------------------------------------------
// Inner form fields (has access to TurnstileContext via hook)
// ---------------------------------------------------------------------------

function CharterApplicationFields({
  source,
  isReady,
}: CharterApplicationFormProps & { isReady: boolean }) {
  const { turnstileToken, honeypot } = useTurnstileProtection();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [trade, setTrade] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [state, setState] = useState("");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState<
    "idle" | "submitting" | "success" | "error"
  >("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [position, setPosition] = useState<number | null>(null);

  // Capture UTM params at mount (not during render)
  const utmRef = useRef<Record<string, string>>({});
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    ["utm_source", "utm_medium", "utm_campaign"].forEach((k) => {
      const v = params.get(k);
      if (v) utmRef.current[k] = v;
    });
  }, []);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    // Client-side validation
    const validationError = validateCharterApplication(
      name,
      email,
      trade,
      companySize,
      state,
    );
    if (validationError) {
      setErrorMsg(validationError);
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

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();

    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/v1/marketing/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedName,
          email: trimmedEmail,
          trade,
          company_size: companySize,
          state, // required, validated above
          notes: notes.trim() || undefined, // optional — omit if empty
          source: source ?? "charter_page",
          cf_turnstile_response: turnstileToken,
          honeypot,
          ...utmRef.current,
        }),
      });

      if (res.ok || res.status === 200) {
        const data = await res.json();
        setPosition(data.position ?? null);
        setStatus("success");
      } else {
        const data = await res.json().catch(() => ({}));
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
      setErrorMsg(
        "Unable to connect. Please check your connection and try again.",
      );
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div
        className="rounded-xl p-8 text-center"
        style={{
          background: "var(--margin-50)",
          border: "var(--divider-thin) solid var(--margin-400)",
        }}
        role="status"
        aria-live="polite"
      >
        <div className="text-4xl mb-4">🎉</div>
        <h3
          className="text-xl font-bold mb-2"
          style={{ color: "var(--neutral-900)" }}
        >
          You{"'"}re in!
        </h3>
        <p className="text-base" style={{ color: "var(--neutral-600)" }}>
          We will reach out to you to discuss onboarding to the Charter Crew.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Name (required) */}
      <div>
        <label
          htmlFor="charter-name"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Your Name <span aria-label="required">*</span>
        </label>
        <input
          id="charter-name"
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          className="w-full px-4 py-3 rounded-lg text-base"
          style={{
            border: "var(--divider-thin) solid var(--neutral-200)",
            background: "var(--white)",
            color: "var(--neutral-900)",
            outline: "none",
          }}
          onFocus={(e) =>
            (e.currentTarget.style.borderColor = "var(--brand-600)")
          }
          onBlur={(e) =>
            (e.currentTarget.style.borderColor = "var(--neutral-200)")
          }
          autoComplete="name"
        />
      </div>

      {/* Email */}
      <div>
        <label
          htmlFor="charter-email"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Work email <span aria-label="required">*</span>
        </label>
        <input
          id="charter-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          className="w-full px-4 py-3 rounded-lg text-base"
          style={{
            border: "var(--divider-thin) solid var(--neutral-200)",
            background: "var(--white)",
            color: "var(--neutral-900)",
            outline: "none",
          }}
          onFocus={(e) =>
            (e.currentTarget.style.borderColor = "var(--brand-600)")
          }
          onBlur={(e) =>
            (e.currentTarget.style.borderColor = "var(--neutral-200)")
          }
          autoComplete="email"
        />
      </div>

      {/* Trade */}
      <div>
        <label
          htmlFor="charter-trade"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Your trade <span aria-label="required">*</span>
        </label>
        <select
          id="charter-trade"
          required
          value={trade}
          onChange={(e) => setTrade(e.target.value)}
          className="w-full px-4 py-3 rounded-lg text-base"
          style={{
            border: "var(--divider-thin) solid var(--neutral-200)",
            background: "var(--white)",
            color: trade ? "var(--neutral-900)" : "var(--neutral-400)",
            outline: "none",
            appearance: "none",
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16' fill='none'%3E%3Cpath d='M4 6l4 4 4-4' stroke='%23A8A29E' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 12px center",
            paddingRight: "40px",
          }}
          onFocus={(e) =>
            (e.currentTarget.style.borderColor = "var(--brand-600)")
          }
          onBlur={(e) =>
            (e.currentTarget.style.borderColor = "var(--neutral-200)")
          }
        >
          <option value="" disabled>
            Select your trade
          </option>
          <option value="electrical">⚡ Electrical</option>
          <option value="plumbing">💧 Plumbing</option>
          <option value="hvac">❄️ HVAC</option>
          <option value="other">Other</option>
        </select>
      </div>

      {/* State / Location */}
      <div>
        <label
          htmlFor="charter-state"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Your state <span aria-label="required">*</span>
        </label>
        <select
          id="charter-state"
          required
          value={state}
          onChange={(e) => setState(e.target.value)}
          className="w-full px-4 py-3 rounded-lg text-base"
          style={{
            border: "var(--divider-thin) solid var(--neutral-200)",
            background: "var(--white)",
            color: state ? "var(--neutral-900)" : "var(--neutral-400)",
            outline: "none",
            appearance: "none",
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16' fill='none'%3E%3Cpath d='M4 6l4 4 4-4' stroke='%23A8A29E' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 12px center",
            paddingRight: "40px",
          }}
          onFocus={(e) =>
            (e.currentTarget.style.borderColor = "var(--brand-600)")
          }
          onBlur={(e) =>
            (e.currentTarget.style.borderColor = "var(--neutral-200)")
          }
        >
          <option value="" disabled>
            Select your state
          </option>
          {US_STATES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Company size */}
      <fieldset>
        <legend
          className="block text-sm font-medium mb-2"
          style={{ color: "var(--neutral-700)" }}
        >
          Team size <span aria-label="required">*</span>
        </legend>
        <div className="flex flex-wrap gap-2">
          {[
            { value: "solo", label: "Solo" },
            { value: "2-5", label: "2–5" },
            { value: "6-10", label: "6–10" },
            { value: "10+", label: "10+" },
          ].map((s) => (
            <label key={s.value} className="cursor-pointer">
              <input
                type="radio"
                name="company_size"
                value={s.value}
                checked={companySize === s.value}
                onChange={() => setCompanySize(s.value)}
                className="sr-only"
                required={!companySize}
              />
              <span
                className="inline-block px-4 py-2 rounded-full text-sm font-medium border transition-all"
                style={{
                  background:
                    companySize === s.value
                      ? "var(--brand-600)"
                      : "var(--white)",
                  color:
                    companySize === s.value
                      ? "var(--white)"
                      : "var(--neutral-700)",
                  borderColor:
                    companySize === s.value
                      ? "var(--brand-600)"
                      : "var(--neutral-200)",
                }}
              >
                {s.label}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Notes (optional) */}
      <div>
        <label
          htmlFor="charter-notes"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Anything you{"'"}d like us to know?{" "}
          <span className="font-normal" style={{ color: "var(--neutral-400)" }}>
            (optional)
          </span>
        </label>
        <textarea
          id="charter-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Tell us about your business, what you're struggling with, or anything else."
          rows={3}
          className="w-full px-4 py-3 rounded-lg text-base resize-y"
          style={{
            border: "var(--divider-thin) solid var(--neutral-200)",
            background: "var(--white)",
            color: "var(--neutral-900)",
            outline: "none",
            minHeight: "80px",
          }}
          onFocus={(e) =>
            (e.currentTarget.style.borderColor = "var(--brand-600)")
          }
          onBlur={(e) =>
            (e.currentTarget.style.borderColor = "var(--neutral-200)")
          }
        />
      </div>

      {status === "error" && errorMsg && <FormErrorAlert message={errorMsg} />}

      <button
        type="submit"
        className="btn-primary w-full"
        disabled={status === "submitting" || !isReady}
        aria-busy={status === "submitting"}
        onClick={handleSubmit as never}
      >
        {status === "submitting" ? (
          <span className="flex items-center gap-2">
            <SubmitSpinner />
            Joining Charter...
          </span>
        ) : (
          "Be one of the first twelve"
        )}
      </button>

      <p
        className="text-xs text-center"
        style={{ color: "var(--neutral-400)" }}
      >
        No credit card required · Takes 10 seconds
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public export — wraps fields in TurnstileProtectedForm
// ---------------------------------------------------------------------------

export default function CharterApplicationForm({
  source = "charter_page",
}: CharterApplicationFormProps) {
  return (
    <TurnstileProtectedForm
      ariaLabel="Join the Charter program"
      onSubmit={(e) => e.preventDefault()}
    >
      {({ isReady }) => (
        <CharterApplicationFields source={source} isReady={isReady} />
      )}
    </TurnstileProtectedForm>
  );
}
