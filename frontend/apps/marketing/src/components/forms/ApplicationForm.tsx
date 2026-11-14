/**
 * ApplicationForm — MKT-B6
 *
 * Job application form for the careers page.
 * Extends <TurnstileProtectedForm> for shared Turnstile + honeypot security.
 * POSTs to POST /api/v1/marketing/application.
 *
 * Validation: trim, email regex, URL prefix check, required dropdowns,
 *             required name/email, min length on why_interested.
 */

"use client";

import { useState } from "react";
import TurnstileProtectedForm, {
  useTurnstileProtection,
  SubmitSpinner,
  FormErrorAlert,
} from "./TurnstileProtectedForm";

// ---------------------------------------------------------------------------
// Role data — env var driven with hardcoded fallback
// ---------------------------------------------------------------------------

const DEFAULT_ROLES = [
  "AI / ML Engineer",
  "Full-Stack Engineer (Trades Domain)",
  "Customer Success (Trades Background a Plus)",
  "Sales / Growth",
];

const OPEN_ROLES =
  process.env.NEXT_PUBLIC_CAREERS_OPEN_ROLES?.split(",")
    .map((r) => r.trim())
    .filter(Boolean) ?? DEFAULT_ROLES;

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

// Requires 2+ char TLD — catches me@me.t which browser type="email" allows
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const WHY_INTERESTED_MIN = 30;

function isValidUrl(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.startsWith("http://") || trimmed.startsWith("https://");
}

function validateApplication(
  name: string,
  email: string,
  role: string,
  linkedinUrl: string,
  portfolioUrl: string,
  whyInterested: string,
): string | null {
  if (!name.trim()) return "Please enter your full name.";
  if (!email.trim()) return "Please enter your email address.";
  if (!EMAIL_REGEX.test(email.trim()))
    return "Please enter a valid email address.";
  if (!role) return "Please select the role you are applying for.";
  if (!linkedinUrl.trim()) return "Please enter your LinkedIn profile URL.";
  if (!isValidUrl(linkedinUrl))
    return "LinkedIn URL must start with https:// (e.g., https://linkedin.com/in/your-name).";
  if (portfolioUrl.trim() && !isValidUrl(portfolioUrl))
    return "Portfolio URL must start with https:// (e.g., https://github.com/your-handle).";
  if (!whyInterested.trim())
    return "Please tell us why you're interested in joining the team.";
  if (whyInterested.trim().length < WHY_INTERESTED_MIN)
    return `Please write at least ${WHY_INTERESTED_MIN} characters in your answer.`;
  return null;
}

// ---------------------------------------------------------------------------
// Shared style constants (matches ContactForm)
// ---------------------------------------------------------------------------

const SELECT_BG = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16' fill='none'%3E%3Cpath d='M4 6l4 4 4-4' stroke='%23A8A29E' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`;

const inputStyle = {
  border: "var(--divider-thin) solid var(--neutral-200)",
  background: "var(--white)",
  color: "var(--neutral-900)",
  outline: "none",
} as const;

// ---------------------------------------------------------------------------
// Inner form fields (has access to TurnstileContext via hook)
// ---------------------------------------------------------------------------

function ApplicationFields({ isReady }: { isReady: boolean }) {
  const { turnstileToken, honeypot } = useTurnstileProtection();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [whyInterested, setWhyInterested] = useState("");
  const [status, setStatus] = useState<
    "idle" | "submitting" | "success" | "error"
  >("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const focusHandler = (
    e: React.FocusEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >,
  ) => {
    e.currentTarget.style.borderColor = "var(--brand-600)";
  };
  const blurHandler = (
    e: React.FocusEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >,
  ) => {
    e.currentTarget.style.borderColor = "var(--neutral-200)";
  };

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    // Client-side validation
    const validationError = validateApplication(
      name,
      email,
      role,
      linkedinUrl,
      portfolioUrl,
      whyInterested,
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
    const trimmedLinkedin = linkedinUrl.trim();
    const trimmedPortfolio = portfolioUrl.trim();
    const trimmedWhy = whyInterested.trim();

    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/v1/marketing/application`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedName,
          email: trimmedEmail,
          role,
          linkedin_url: trimmedLinkedin,
          portfolio_url: trimmedPortfolio || null,
          why_interested: trimmedWhy,
          source_page: "/careers",
          cf_turnstile_response: turnstileToken ?? "",
          honeypot,
        }),
      });

      if (res.status === 201 || res.ok) {
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
        className="rounded-xl p-6"
        style={{
          background: "var(--margin-50)",
          border: "var(--divider-thin) solid var(--margin-400)",
        }}
        role="status"
        aria-live="polite"
      >
        <p
          className="text-lg font-semibold mb-2"
          style={{ color: "var(--neutral-900)" }}
        >
          ✓ Application received!
        </p>
        <p className="text-base" style={{ color: "var(--neutral-700)" }}>
          We review every application personally. If it&apos;s a fit,
          you&apos;ll hear from us at{" "}
          <span className="font-medium" style={{ color: "var(--neutral-900)" }}>
            {email}
          </span>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Name */}
      <div>
        <label
          htmlFor="app-name"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Full Name <span aria-label="required">*</span>
        </label>
        <input
          id="app-name"
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your full name"
          className="w-full px-4 py-3 rounded-lg text-base"
          style={inputStyle}
          onFocus={focusHandler}
          onBlur={blurHandler}
          autoComplete="name"
        />
      </div>

      {/* Email */}
      <div>
        <label
          htmlFor="app-email"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Email Address <span aria-label="required">*</span>
        </label>
        <input
          id="app-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          className="w-full px-4 py-3 rounded-lg text-base"
          style={inputStyle}
          onFocus={focusHandler}
          onBlur={blurHandler}
          autoComplete="email"
        />
      </div>

      {/* Role */}
      <div>
        <label
          htmlFor="app-role"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Role Applying For <span aria-label="required">*</span>
        </label>
        <select
          id="app-role"
          required
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="w-full px-4 py-3 rounded-lg text-base"
          style={{
            ...inputStyle,
            color: role ? "var(--neutral-900)" : "var(--neutral-400)",
            appearance: "none",
            backgroundImage: SELECT_BG,
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 12px center",
            paddingRight: "40px",
          }}
          onFocus={focusHandler}
          onBlur={blurHandler}
        >
          <option value="" disabled>
            Select a role
          </option>
          {OPEN_ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      {/* LinkedIn URL (required) */}
      <div>
        <label
          htmlFor="app-linkedin"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          LinkedIn Profile URL <span aria-label="required">*</span>
        </label>
        <input
          id="app-linkedin"
          type="url"
          required
          value={linkedinUrl}
          onChange={(e) => setLinkedinUrl(e.target.value)}
          placeholder="https://linkedin.com/in/your-name"
          className="w-full px-4 py-3 rounded-lg text-base"
          style={inputStyle}
          onFocus={focusHandler}
          onBlur={blurHandler}
          autoComplete="url"
        />
      </div>

      {/* Portfolio / GitHub / Personal Site URL (optional) */}
      <div>
        <label
          htmlFor="app-portfolio"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Portfolio / GitHub / Personal Site URL{" "}
          <span
            className="text-xs font-normal"
            style={{ color: "var(--neutral-400)" }}
          >
            (optional)
          </span>
        </label>
        <input
          id="app-portfolio"
          type="url"
          value={portfolioUrl}
          onChange={(e) => setPortfolioUrl(e.target.value)}
          placeholder="https://github.com/your-handle"
          className="w-full px-4 py-3 rounded-lg text-base"
          style={inputStyle}
          onFocus={focusHandler}
          onBlur={blurHandler}
          autoComplete="url"
        />
      </div>

      {/* Why interested */}
      <div>
        <label
          htmlFor="app-why"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Why are you interested in joining our team?{" "}
          <span aria-label="required">*</span>
        </label>
        <textarea
          id="app-why"
          required
          rows={5}
          value={whyInterested}
          onChange={(e) => setWhyInterested(e.target.value)}
          placeholder="Tell us about yourself and why this mission matters to you..."
          maxLength={2000}
          className="w-full px-4 py-3 rounded-lg text-base resize-none"
          style={inputStyle}
          onFocus={focusHandler}
          onBlur={blurHandler}
        />
        <p className="text-xs mt-1" style={{ color: "var(--neutral-400)" }}>
          {whyInterested.length}/2000 characters · minimum {WHY_INTERESTED_MIN}
        </p>
      </div>

      {status === "error" && errorMsg && <FormErrorAlert message={errorMsg} />}

      <button
        type="submit"
        className="btn-primary"
        disabled={status === "submitting" || !isReady}
        aria-busy={status === "submitting"}
        onClick={handleSubmit as never}
      >
        {status === "submitting" ? (
          <span className="flex items-center gap-2">
            <SubmitSpinner />
            Submitting application...
          </span>
        ) : (
          "Submit Application"
        )}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public export — wraps fields in TurnstileProtectedForm
// ---------------------------------------------------------------------------

export default function ApplicationForm() {
  return (
    <TurnstileProtectedForm
      ariaLabel="Job application form"
      onSubmit={(e) => e.preventDefault()}
      className="flex flex-col gap-5"
    >
      {({ isReady }) => <ApplicationFields isReady={isReady} />}
    </TurnstileProtectedForm>
  );
}
