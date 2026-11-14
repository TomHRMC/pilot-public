// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import TradePageTemplate from "../../../components/trades/TradePageTemplate";
import type {
  PainPoint,
  Feature,
  VoiceCard,
  FAQ,
} from "../../../components/trades/TradePageTemplate";
import { getSiteMode } from "../../../lib/useSiteMode";

export const metadata: Metadata = {
  title: "Electrical Contractor Software — AI Voice Quoting & Estimating",
  description:
    "Built for electricians. Voice-powered quoting with NEC compliance, real-time copper pricing, and panel upgrade estimates in minutes — not hours. Start your free trial.",
  keywords: [
    "electrical estimating software",
    "electrical contractor quoting",
    "electrician business software",
    "electrical contractor software",
  ],
  openGraph: {
    title:
      "Electrical Contractor Software — AI Voice Quoting & Estimating | Pilot for Trades",
    description:
      "Built for electricians. Voice-powered quoting with NEC compliance, real-time copper pricing, and panel upgrade estimates in minutes — not hours.",
    url: "https://pilotfortrades.com/trades/electrical",
    images: [
      {
        url: "/og-trades-electrical.png",
        width: 1200,
        height: 630,
        alt: "Pilot for Trades — AI Voice Quoting for Electricians",
      },
    ],
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    {
      "@type": "ListItem",
      position: 1,
      name: "Home",
      item: "https://pilotfortrades.com",
    },
    {
      "@type": "ListItem",
      position: 2,
      name: "Trades",
      item: "https://pilotfortrades.com/trades/electrical",
    },
    {
      "@type": "ListItem",
      position: 3,
      name: "Electrical",
      item: "https://pilotfortrades.com/trades/electrical",
    },
  ],
};

const painPoints: PainPoint[] = [
  {
    iconName: "BookOpen",
    stat: "NEC Compliance",
    title: "Code Changes Every 3 Years",
    description:
      "NEC 2023 introduced 75+ revisions. Keeping every quote code-compliant while working in the field is a full-time job on top of your full-time job.",
  },
  {
    iconName: "TrendingUp",
    stat: "Copper Up 40%",
    title: "Wire Prices Won't Sit Still",
    description:
      "Copper and aluminum prices have swung 40% in 18 months. Quote a panel upgrade on Monday with last month's prices and you're eating the difference by Friday.",
  },
  {
    iconName: "Clock",
    stat: "3+ Hours Per Quote",
    title: "Panel Upgrades Take All Night",
    description:
      "A 200A residential panel upgrade quote means counting breakers, sizing feeders, checking load calcs, pricing materials, and building the estimate — from scratch, every time.",
  },
];

const features: Feature[] = [
  {
    iconName: "Mic",
    title: "Talk Through the Job. Get the Quote.",
    description:
      'Walk the panel, describe what you see, and Pilot builds the estimate. "200-amp panel upgrade, 42-space, Square D QO, 150 feet of 2/0 copper." Materials, labor, markup — done.',
    linkLabel: "See Voice AI →",
    linkHref: "/features#voice-ai",
  },
  {
    iconName: "DollarSign",
    title: "Today's Wire Prices. Not Last Month's.",
    description:
      "Pilot tracks copper, aluminum, conduit, and fixture pricing in real time. Your quotes reflect what materials actually cost — not what they cost when you last checked.",
    linkLabel: "See Pricing Engine →",
    linkHref: "/features#quoting",
  },
  {
    iconName: "Shield",
    title: "Code Compliance Built In",
    description:
      "Voltage drop? Conduit fill? Ampacity tables? Pilot references NEC 2023 so your estimates meet code requirements without flipping through the codebook on-site.",
    linkLabel: "See AI Help →",
    linkHref: "/features#help",
  },
  {
    iconName: "BarChart3",
    title: "Know Your Margin Before You Leave",
    description:
      'Real-time job costing tracks materials, labor hours, and expenses as they happen. No more "I think we made money on that job" — you know, in real time.',
    linkLabel: "See Profitability →",
    linkHref: "/features#profitability",
  },
];

const voiceExamples: VoiceCard[] = [
  {
    command:
      "Quote a 200-amp panel upgrade for a 2,400 square foot house, Square D QO, 42 spaces, existing service is 100-amp Federal Pacific.",
    response:
      "Panel, breakers, feeder wire, grounding, permit, labor — full line-item estimate generated.",
  },
  {
    command:
      "Add 150 feet of 2/0 copper THWN in 2-inch EMT, four conductors plus ground.",
    response:
      "Materials added with today's copper pricing, conduit fill calculated at 28% (within NEC 40% limit).",
  },
  {
    command:
      "What's the voltage drop on a 200-foot run of #10 copper at 30 amps?",
    response:
      "6.2% voltage drop at 240 V — above the 3% branch-circuit recommendation in the NEC 210.19(A) informational note. Upsizing to #6 copper brings it to about 2.5%.",
  },
];

const faqs: FAQ[] = [
  {
    question: "Does Pilot actually understand NEC codes?",
    answer:
      "Yes. Pilot's AI references NEC 2023 for voltage drop calculations, conduit fill ratios, ampacity tables, and common residential/commercial requirements. It's not a replacement for your professional judgment — it's a tool that helps you build code-aware estimates faster.",
  },
  {
    question: "Can I quote a full panel upgrade by voice?",
    answer:
      "Absolutely. Walk the existing panel, describe what you see, and tell Pilot what you're installing. It generates a full line-item estimate — panel, breakers, feeder wire, grounding, labor, permit fees, and your markup. A 200A residential upgrade quote that takes 2–3 hours manually takes about 5 minutes with Pilot.",
  },
  {
    question: "How does Pilot handle copper price changes?",
    answer:
      "Pilot tracks real-time material pricing for copper, aluminum, common wire gauges, conduit, panels, and breakers. When you create a quote, it uses today's prices — not whatever you last entered in a spreadsheet. No more eating a price spike because your numbers were stale.",
  },
  {
    question: "I work solo. Is this overkill for a one-person shop?",
    answer:
      "It's built for you. Pilot is $49/month, everything included — designed for solo and small electrical contractors. You're the exact person losing 15 hours a week to admin because you don't have an office manager. Pilot is your digital office manager — except it never calls in sick.",
  },
  {
    question: "Does Pilot sync with QuickBooks?",
    answer:
      "Yes. Bi-directional QuickBooks Online sync pushes invoices, payments, and customer records automatically. Your books stay in QuickBooks; Pilot handles the field work. No double entry.",
  },
  {
    question: "What if I'm on a job site with no cell signal?",
    answer:
      "Pilot works offline. Create quotes, log time, capture job photos — everything syncs automatically when you're back in range. No lost work. Built for basements, attics, and dead zones.",
  },
  {
    question: "Can my guys use it too, or just me?",
    answer:
      "Every plan includes unlimited users. Your techs can log time, update job status, and capture photos in the field. You control what they see and what they don't through role-based permissions.",
  },
];

export default async function ElectricalTradePage() {
  const { mode } = await getSiteMode();
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <TradePageTemplate
        trade="electrical"
        accentToken="--trade-electrical"
        heroBadge="Built for Electrical Contractors"
        heroHeadline="The AI Copilot for Electrical Contractors"
        heroSubheadline="Stop spending your evenings on estimates. Pilot builds code-compliant quotes by voice — voltage drop, conduit fill, ampacity — while you're still on the ladder."
        heroImageAlt="Electrician on job site using Pilot voice quoting on phone — commercial panel in background"
        painSectionHeading="Every Electrician Knows These Problems"
        painSectionSubtitle="You got your license to do electrical work — not to wrestle spreadsheets at 9 PM."
        painPoints={painPoints}
        featureSectionHeading="What Pilot Does for Electricians"
        featureSectionSubtitle="The same tools you'd build yourself if you had a dev team and 10,000 hours."
        features={features}
        voiceSectionHeading="Pilot Speaks Electrician"
        voiceSectionSubtitle="Not generic 'contractor software' that doesn't know a romex from a raceway."
        voiceExamples={voiceExamples}
        voiceBodyCopy="Pilot's Voice AI understands electrical terminology, NEC references, manufacturer part numbers, and trade shorthand. It's not a chatbot pretending to be useful — it's a quoting engine that happens to listen."
        pricingSectionHeading="Built for Your Electrical Business"
        pricingBodyCopy="$49/month, everything included. One platform for quoting, dispatch, invoicing, profitability tracking, and QuickBooks sync. Saves 15+ hours per week in admin time — that's $750+ worth of billable hours back in your pocket."
        faqSectionHeading="Common Questions from Electricians"
        faqs={faqs}
        finalCtaHeadline="Join the Electricians Shaping Pilot"
        finalCtaBody="Pilot for Trades is built by people who understand the trades. Be one of the first twelve, lock in Charter pricing, and help shape the tool that gives electricians their evenings back."
        siteMode={mode}
      />
    </>
  );
}
