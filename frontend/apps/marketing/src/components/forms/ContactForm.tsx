/**
 * ContactForm — UPDATED for MKT-B1.5, MKT-B6
 *
 * MKT-B6 changes:
 *   - Client-side validation: trim, email regex, required dropdown, min message length
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import TurnstileProtectedForm, {
  useTurnstileProtection,
  SubmitSpinner,
  FormErrorAlert,
} from "./TurnstileProtectedForm";

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

// Requires 2+ char TLD — catches me@me.t which browser type="email" allows
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const MESSAGE_MIN_LENGTH = 20;

function validateContact(
  name: string,
  email: string,
  subject: string,
  message: string,
): string | null {
  if (!name.trim()) return "Please enter your name.";
  if (!email.trim()) return "Please enter your email address.";
  if (!EMAIL_REGEX.test(email.trim()))
    return "Please enter a valid email address.";
  if (!subject) return "Please select a subject.";
  if (!message.trim()) return "Please enter your message.";
  if (message.trim().length < MESSAGE_MIN_LENGTH)
    return `Please enter at least ${MESSAGE_MIN_LENGTH} characters in your message.`;
  return null;
}

// ---------------------------------------------------------------------------
// Inner form fields
// ---------------------------------------------------------------------------

const SELECT_BG = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16' fill='none'%3E%3Cpath d='M4 6l4 4 4-4' stroke='%23A8A29E' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`;

function ContactFields({ isReady }: { isReady: boolean }) {
  const { turnstileToken, honeypot } = useTurnstileProtection();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<
    "idle" | "submitting" | "success" | "error"
  >("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    // Client-side validation
    const validationError = validateContact(name, email, subject, message);
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
    const trimmedMessage = message.trim();

    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${apiBase}/api/v1/marketing/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedName,
          email: trimmedEmail,
          subject,
          message: trimmedMessage,
          source_page: "/contact",
          cf_turnstile_response: turnstileToken,
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
        "Unable to connect. Please try again or email info@pilotfortrades.com directly.",
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
          ✓ Message sent!
        </p>
        <p className="text-base" style={{ color: "var(--neutral-700)" }}>
          We&apos;ll get back to you within 24 hours. In the meantime, check out
          our{" "}
          <Link href="/features" style={{ color: "var(--brand-600)" }}>
            Features
          </Link>{" "}
          to see what Pilot can do.
        </p>
      </div>
    );
  }

  const inputStyle = {
    border: "var(--divider-thin) solid var(--neutral-200)",
    background: "var(--white)",
    color: "var(--neutral-900)",
    outline: "none",
  };

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

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col sm:flex-row gap-5">
        <div className="flex-1">
          <label
            htmlFor="contact-name"
            className="block text-sm font-medium mb-1"
            style={{ color: "var(--neutral-700)" }}
          >
            Name <span aria-label="required">*</span>
          </label>
          <input
            id="contact-name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="w-full px-4 py-3 rounded-lg text-base"
            style={inputStyle}
            onFocus={focusHandler}
            onBlur={blurHandler}
            autoComplete="name"
          />
        </div>
        <div className="flex-1">
          <label
            htmlFor="contact-email"
            className="block text-sm font-medium mb-1"
            style={{ color: "var(--neutral-700)" }}
          >
            Email <span aria-label="required">*</span>
          </label>
          <input
            id="contact-email"
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
      </div>

      <div>
        <label
          htmlFor="contact-subject"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Subject <span aria-label="required">*</span>
        </label>
        <select
          id="contact-subject"
          required
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="w-full px-4 py-3 rounded-lg text-base"
          style={{
            ...inputStyle,
            color: subject ? "var(--neutral-900)" : "var(--neutral-400)",
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
            Select a subject
          </option>
          <option value="General Inquiry">General Inquiry</option>
          <option value="Sales Question">Sales Question</option>
          <option value="Technical Support">Technical Support</option>
          <option value="Partnership Opportunity">
            Partnership Opportunity
          </option>
        </select>
      </div>

      <div>
        <label
          htmlFor="contact-message"
          className="block text-sm font-medium mb-1"
          style={{ color: "var(--neutral-700)" }}
        >
          Message <span aria-label="required">*</span>
        </label>
        <textarea
          id="contact-message"
          required
          rows={5}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Tell us what's on your mind..."
          maxLength={5000}
          className="w-full px-4 py-3 rounded-lg text-base resize-none"
          style={inputStyle}
          onFocus={focusHandler}
          onBlur={blurHandler}
        />
        <p className="text-xs mt-1" style={{ color: "var(--neutral-400)" }}>
          {message.length}/5000 characters · minimum {MESSAGE_MIN_LENGTH}
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
            Sending...
          </span>
        ) : (
          "Send Message"
        )}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public export
// ---------------------------------------------------------------------------

export default function ContactForm() {
  return (
    <TurnstileProtectedForm
      ariaLabel="Contact form"
      onSubmit={(e) => e.preventDefault()}
      className="flex flex-col gap-5"
    >
      {({ isReady }) => <ContactFields isReady={isReady} />}
    </TurnstileProtectedForm>
  );
}
