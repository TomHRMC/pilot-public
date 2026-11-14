"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import type { SiteMode } from "@/lib/useSiteMode";

/* ─── Types ─────────────────────────────────────────── */

export interface PainPoint {
  iconName: string;
  stat: string;
  title: string;
  description: string;
}

export interface Feature {
  iconName: string;
  title: string;
  description: string;
  linkLabel: string;
  linkHref: string;
}

export interface VoiceCard {
  command: string;
  response: string;
}

export interface FAQ {
  question: string;
  answer: string;
}

export interface TradePageProps {
  trade: "electrical" | "plumbing" | "hvac";
  accentToken: string; // CSS custom property name e.g. "--trade-electrical"
  heroBadge: string;
  heroHeadline: string;
  heroSubheadline: string;
  heroImageAlt: string;
  painSectionHeading: string;
  painSectionSubtitle: string;
  painPoints: PainPoint[];
  featureSectionHeading: string;
  featureSectionSubtitle: string;
  features: Feature[];
  voiceSectionHeading: string;
  voiceSectionSubtitle: string;
  voiceExamples: VoiceCard[];
  voiceBodyCopy: string;
  pricingSectionHeading: string;
  pricingBodyCopy: string;
  faqSectionHeading: string;
  faqs: FAQ[];
  finalCtaHeadline: string;
  finalCtaBody: string;
  /** Site operating mode — passed from server component parent */
  siteMode?: SiteMode;
}

/* ─── Icon map (subset of Lucide SVG paths) ────────── */
/* Lucide icons: https://lucide.dev — ISC License, Copyright (c) Lucide Contributors */
const ICONS: Record<string, React.ReactElement> = {
  BookOpen: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  ),
  TrendingUp: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </svg>
  ),
  Clock: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  Mic: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  ),
  DollarSign: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  Shield: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  BarChart3: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 3v18h18" />
      <path d="M18 17V9" />
      <path d="M13 17V5" />
      <path d="M8 17v-3" />
    </svg>
  ),
  RefreshCw: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  ),
  Phone: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.22h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  ),
  Calculator: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <line x1="8" y1="6" x2="16" y2="6" />
      <line x1="8" y1="10" x2="8" y2="10" />
      <line x1="12" y1="10" x2="12" y2="10" />
      <line x1="16" y1="10" x2="16" y2="10" />
      <line x1="8" y1="14" x2="8" y2="14" />
      <line x1="12" y1="14" x2="12" y2="14" />
      <line x1="16" y1="14" x2="16" y2="14" />
      <line x1="8" y1="18" x2="12" y2="18" />
      <line x1="16" y1="18" x2="16" y2="18" />
    </svg>
  ),
  Siren: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M7 12a5 5 0 0 1 5-5v0a5 5 0 0 1 5 5v6H7v-6z" />
      <path d="M5 20h14" />
      <path d="M12 7V3" />
      <path d="M4.22 10.22l1.42-1.42" />
      <path d="M18.36 8.8l1.42 1.42" />
    </svg>
  ),
  Thermometer: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
    </svg>
  ),
  CalendarDays: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <line x1="8" y1="14" x2="8" y2="14" />
      <line x1="12" y1="14" x2="12" y2="14" />
      <line x1="16" y1="14" x2="16" y2="14" />
    </svg>
  ),
  Calendar: (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  ),
};

function Icon({ name, accentColor }: { name: string; accentColor: string }) {
  const icon = ICONS[name];
  if (!icon) return null;
  return (
    <span style={{ color: accentColor, display: "inline-flex" }}>{icon}</span>
  );
}

/* ─── FAQ Accordion ──────────────────────────────────── */
function FaqItem({
  question,
  answer,
  accentColor,
}: {
  question: string;
  answer: string;
  accentColor: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="faq-item">
      <button
        className="faq-button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span>{question}</span>
        <svg
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          aria-hidden="true"
          style={{
            transition: "transform 0.2s",
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            color: open ? accentColor : "var(--neutral-400)",
          }}
        >
          <path
            d="M5 8l5 5 5-5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      {open && (
        <div className="pb-4 pt-1">
          <p className="text-base" style={{ color: "var(--neutral-600)" }}>
            {answer}
          </p>
        </div>
      )}
    </div>
  );
}

/* ─── Main Template ──────────────────────────────────── */
export default function TradePageTemplate({
  trade,
  accentToken,
  heroBadge,
  heroHeadline,
  heroSubheadline,
  heroImageAlt,
  painSectionHeading,
  painSectionSubtitle,
  painPoints,
  featureSectionHeading,
  featureSectionSubtitle,
  features,
  voiceSectionHeading,
  voiceSectionSubtitle,
  voiceExamples,
  voiceBodyCopy,
  pricingSectionHeading,
  pricingBodyCopy,
  faqSectionHeading,
  faqs,
  finalCtaHeadline,
  finalCtaBody,
  siteMode = "charter",
}: TradePageProps) {
  const isGeneral = siteMode === "general";
  const ctaText = isGeneral ? "Start Free Trial" : "Be one of the first twelve";
  const ctaHref = isGeneral ? "/sign-up" : "/charter";
  const pricingBodyResolved = isGeneral
    ? "Starter from $49/month · Teams from $149/month (billed annually)"
    : pricingBodyCopy;
  const accentColor = `var(${accentToken})`;
  // 10% opacity bg: we use inline style with the hex derived from token
  const accentLightBg =
    trade === "electrical"
      ? "var(--trade-electrical-10)"
      : trade === "plumbing"
        ? "var(--trade-plumbing-10)"
        : "var(--trade-hvac-10)";

  const heroGradientStart =
    trade === "electrical"
      ? "var(--trade-electrical-85)"
      : trade === "plumbing"
        ? "var(--trade-plumbing-85)"
        : "var(--trade-hvac-85)";

  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />

      {/* ── Section 1: Trade Hero ── */}
      <section
        className="hero-padding"
        style={{
          background: `linear-gradient(135deg, ${heroGradientStart} 0%, var(--neutral-900) 100%)`,
        }}
        aria-labelledby={`${trade}-hero-heading`}
      >
        <div className="container-marketing">
          <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
            {/* Text column */}
            <div className="flex-1 max-w-2xl">
              {/* Badge */}
              <div className="inline-flex items-center mb-6">
                <span
                  className="text-caption-lg font-semibold px-4 py-1 rounded-full"
                  style={{
                    background: accentLightBg,
                    color: "var(--white)",
                    border: `1px solid ${accentColor}`,
                  }}
                >
                  {heroBadge}
                </span>
              </div>

              {/* Headline */}
              <h1
                id={`${trade}-hero-heading`}
                className="text-hero mb-6"
                style={{ color: "var(--white)" }}
              >
                {heroHeadline}
              </h1>

              {/* Subheadline */}
              <p
                className="text-section-subtitle mb-10"
                style={{ color: "var(--white-85)" }}
              >
                {heroSubheadline}
              </p>

              {/* CTAs */}
              <div className="flex flex-col sm:flex-row gap-4 mb-6">
                <Link href={ctaHref} className="btn-white">
                  {ctaText}
                </Link>
                <Link
                  href="/features#voice-ai"
                  className="inline-flex items-center justify-center text-white underline font-semibold text-base hover:opacity-80 transition-opacity"
                >
                  See How It Works
                </Link>
              </div>

              {/* Microcopy */}
              <p className="text-sm" style={{ color: "var(--white-55)" }}>
                {isGeneral
                  ? "14-day free trial · No credit card required"
                  : "No credit card required · Takes 10 seconds"}
              </p>
            </div>

            {/* Illustration column */}
            <div className="flex-1 max-w-md lg:max-w-none w-full">
              <div
                className="w-full rounded-2xl overflow-hidden"
                style={{
                  aspectRatio: "16/10",
                  background: "var(--white-08)",
                  border: "var(--border-white-15)",
                  position: "relative",
                }}
                role="img"
                aria-label={heroImageAlt}
              >
                <Image
                  src={`/trades/${trade}-hero.jpg`}
                  alt={heroImageAlt}
                  fill
                  className="object-cover object-center"
                  sizes="(max-width: 48rem) 100vw, 50vw"
                  priority
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 2: Pain Points ── */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby={`${trade}-pain-heading`}
      >
        <div className="container-marketing">
          <div className="text-center mb-12">
            <h2
              id={`${trade}-pain-heading`}
              className="text-section-title mb-4"
              style={{ color: "var(--neutral-900)" }}
            >
              {painSectionHeading}
            </h2>
            <p
              className="text-section-subtitle max-w-2xl mx-auto"
              style={{ color: "var(--neutral-600)" }}
            >
              {painSectionSubtitle}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {painPoints.map((pp) => (
              <div
                key={pp.title}
                className="bg-white rounded-xl p-8"
                style={{ boxShadow: "var(--shadow-md)" }}
              >
                {/* Icon */}
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center mb-4"
                  style={{ background: accentLightBg }}
                >
                  <Icon name={pp.iconName} accentColor={accentColor} />
                </div>

                {/* Stat */}
                <p
                  className="text-xl font-bold mb-1"
                  style={{ color: accentColor }}
                >
                  {pp.stat}
                </p>

                {/* Title */}
                <h3
                  className="text-lg font-semibold mb-3"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {pp.title}
                </h3>

                {/* Description */}
                <p
                  className="text-base"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {pp.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 3: Feature Highlights ── */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-labelledby={`${trade}-features-heading`}
      >
        <div className="container-marketing">
          <div className="text-center mb-12">
            <h2
              id={`${trade}-features-heading`}
              className="text-section-title mb-4"
              style={{ color: "var(--neutral-900)" }}
            >
              {featureSectionHeading}
            </h2>
            <p
              className="text-section-subtitle max-w-2xl mx-auto"
              style={{ color: "var(--neutral-600)" }}
            >
              {featureSectionSubtitle}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((feat) => (
              <div
                key={feat.title}
                className="rounded-xl p-6 border transition-all"
                style={{
                  background: "var(--neutral-50)",
                  borderColor: "var(--neutral-200)",
                }}
              >
                {/* Icon circle */}
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center mb-4"
                  style={{ background: accentLightBg }}
                >
                  <Icon name={feat.iconName} accentColor={accentColor} />
                </div>

                <h3
                  className="text-xl font-semibold mb-2"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {feat.title}
                </h3>
                <p
                  className="text-base mb-4"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {feat.description}
                </p>
                <Link
                  href={feat.linkHref}
                  className="text-sm font-semibold"
                  style={{ color: "var(--brand-600)" }}
                >
                  {feat.linkLabel}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 4: Voice AI ── */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing-alt)" }}
        aria-labelledby={`${trade}-voice-heading`}
      >
        <div className="container-marketing">
          <div className="mb-10">
            <h2
              id={`${trade}-voice-heading`}
              className="text-section-title mb-4"
              style={{ color: "var(--neutral-900)" }}
            >
              {voiceSectionHeading}
            </h2>
            <p
              className="text-section-subtitle max-w-2xl"
              style={{ color: "var(--neutral-600)" }}
            >
              {voiceSectionSubtitle}
            </p>
          </div>

          {/* Voice cards */}
          <div className="flex flex-col gap-6 max-w-3xl mb-10">
            {voiceExamples.map((card, i) => (
              <div
                key={i}
                className="bg-white rounded-xl p-6"
                style={{
                  borderLeft: `4px solid ${accentColor}`,
                  boxShadow: "var(--shadow-xs)",
                }}
              >
                {/* Command */}
                <div
                  className="rounded-lg p-4 mb-3 flex items-start gap-3"
                  style={{ background: "var(--neutral-50)" }}
                >
                  <span style={{ color: accentColor, flexShrink: 0 }}>
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                    </svg>
                  </span>
                  <p
                    className="text-base font-medium"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    &ldquo;{card.command}&rdquo;
                  </p>
                </div>

                {/* Response */}
                <div className="flex items-start gap-3 pl-1">
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                    style={{
                      color: "var(--margin-600)",
                      flexShrink: 0,
                      marginTop: "var(--divider-thick)",
                    }}
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <p
                    className="text-base"
                    style={{ color: "var(--neutral-600)" }}
                  >
                    {card.response}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Body copy */}
          <p
            className="text-body-lg max-w-2xl"
            style={{ color: "var(--neutral-700)" }}
          >
            {voiceBodyCopy}
          </p>
        </div>
      </section>

      {/* ── Section 5: Pricing CTA ── */}
      <section
        className="py-16"
        style={{ background: "var(--brand-600)" }}
        aria-labelledby={`${trade}-pricing-heading`}
      >
        <div className="container-marketing text-center max-w-2xl mx-auto">
          <h2
            id={`${trade}-pricing-heading`}
            className="text-section-title mb-4"
            style={{ color: "var(--white)" }}
          >
            {pricingSectionHeading}
          </h2>
          <p className="text-body-lg mb-8" style={{ color: "var(--white-82)" }}>
            {pricingBodyResolved}
          </p>
          {isGeneral && (
            <p className="text-sm mb-4" style={{ color: "var(--white-7)" }}>
              14-day free trial — no credit card required.
            </p>
          )}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href={ctaHref} className="btn-white">
              {ctaText}
            </Link>
            <Link
              href="/pricing"
              className="text-white underline font-semibold text-base hover:opacity-80 transition-opacity self-center"
            >
              See full pricing →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Section 6: FAQ ── */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-labelledby={`${trade}-faq-heading`}
      >
        <div className="container-marketing max-w-3xl mx-auto">
          <h2
            id={`${trade}-faq-heading`}
            className="text-section-title text-center mb-12"
            style={{ color: "var(--neutral-900)" }}
          >
            {faqSectionHeading}
          </h2>
          <div>
            {faqs.map((faq) => (
              <FaqItem
                key={faq.question}
                question={faq.question}
                answer={faq.answer}
                accentColor={accentColor}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 7: Final CTA ── */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby={`${trade}-final-cta-heading`}
      >
        <div className="container-marketing text-center max-w-2xl mx-auto">
          <h2
            id={`${trade}-final-cta-heading`}
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            {finalCtaHeadline}
          </h2>
          <p
            className="text-body-lg mb-10"
            style={{ color: "var(--neutral-600)" }}
          >
            {finalCtaBody}
          </p>
          <Link href={ctaHref} className="btn-primary">
            {ctaText}
          </Link>
          <p className="text-sm mt-4" style={{ color: "var(--neutral-500)" }}>
            {isGeneral
              ? "14-day free trial · No credit card required"
              : "No credit card required · Takes 10 seconds"}
          </p>
        </div>
      </section>
    </>
  );
}
