import Link from "next/link";
import type { SiteMode } from "@/lib/useSiteMode";

interface BlogCtaProps {
  headline?: string;
  body?: string;
  ctaLabel?: string;
  ctaHref?: string;
  /** Site operating mode — controls default CTA label/href and subtext */
  siteMode?: SiteMode;
}

export default function BlogCta({
  headline = "Ready to try voice quoting?",
  body = "Pilot builds estimates by voice — NEC-aware, real-time pricing, hands-free.",
  ctaLabel,
  ctaHref,
  siteMode = "charter",
}: BlogCtaProps) {
  const isGeneral = siteMode === "general";

  // Allow explicit overrides; fall back to mode-aware defaults
  const resolvedCtaLabel =
    ctaLabel ??
    (isGeneral ? "Start Free Trial →" : "Be one of the first twelve →");
  const resolvedCtaHref = ctaHref ?? (isGeneral ? "/sign-up" : "/charter");

  return (
    <aside
      className="rounded-xl p-6 my-8"
      style={{
        background: "var(--brand-50)",
        border: "var(--divider-thin) solid var(--brand-100)",
      }}
      aria-label="Call to action"
    >
      <h3
        className="text-lg font-semibold mb-2"
        style={{ color: "var(--brand-900)" }}
      >
        {headline}
      </h3>
      <p className="text-base mb-4" style={{ color: "var(--brand-800)" }}>
        {body}
      </p>
      <Link
        href={resolvedCtaHref}
        className="btn-primary inline-flex"
        style={{
          fontSize: "0.9375rem",
          padding: "0.75rem 1.5rem",
          color: "var(--white)",
        }}
      >
        {resolvedCtaLabel}
      </Link>
      {isGeneral && (
        <p
          className="mt-2 text-caption-lg"
          style={{ color: "var(--brand-600)" }}
        >
          14 days free · No credit card
        </p>
      )}
    </aside>
  );
}
