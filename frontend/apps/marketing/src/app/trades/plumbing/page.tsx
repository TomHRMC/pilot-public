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
  title: "Plumbing Contractor Software — AI Voice Quoting & Estimating",
  description:
    "Built for plumbers. Voice-powered estimating with real-time fixture pricing, pipe sizing references, and emergency dispatch — all from your phone. Start your free trial.",
  keywords: [
    "plumbing estimating software",
    "plumber business management",
    "plumbing contractor software",
    "plumbing business software",
  ],
  openGraph: {
    title:
      "Plumbing Contractor Software — AI Voice Quoting & Estimating | Pilot for Trades",
    description:
      "Built for plumbers. Voice-powered estimating with real-time fixture pricing, pipe sizing references, and emergency dispatch — all from your phone.",
    url: "https://pilotfortrades.com/trades/plumbing",
    images: [
      {
        url: "/og-trades-plumbing.png",
        width: 1200,
        height: 630,
        alt: "Pilot for Trades — AI Voice Quoting for Plumbers",
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
      item: "https://pilotfortrades.com/trades/plumbing",
    },
    {
      "@type": "ListItem",
      position: 3,
      name: "Plumbing",
      item: "https://pilotfortrades.com/trades/plumbing",
    },
  ],
};

const painPoints: PainPoint[] = [
  {
    iconName: "RefreshCw",
    stat: "Price Swings",
    title: "Fixture Catalogs Change Quarterly",
    description:
      "Supply house pricing updates hit every quarter — sometimes monthly. You quoted a Kohler fixture suite on Tuesday, and by the time the customer says yes on Friday, your cost is $200 higher. That margin difference comes straight out of your pocket.",
  },
  {
    iconName: "Phone",
    stat: "Emergency Calls",
    title: "Dispatch Chaos at 6 AM",
    description:
      "A slab leak on one side of town, a water heater replacement on the other, and your guy just called out sick. Juggling emergency dispatch with sticky notes and group texts doesn't scale past two trucks.",
  },
  {
    iconName: "Calculator",
    stat: "Manual Takeoffs",
    title: "Pipe Sizing Still Done by Hand",
    description:
      "Every bathroom rough-in means counting fixtures, calculating DFUs, sizing supply and waste lines, and pricing every fitting by hand. A whole-house repipe estimate can eat your entire evening.",
  },
];

const features: Feature[] = [
  {
    iconName: "Mic",
    title: "Describe the Job. Get the Estimate.",
    description:
      'Walk the jobsite, talk through what you see: "Whole-house repipe, 2,200 square feet, PEX-A, 14 fixtures, two-story with crawl space access." Pilot builds the estimate while you\'re still on-site.',
    linkLabel: "See Voice AI →",
    linkHref: "/features#voice-ai",
  },
  {
    iconName: "DollarSign",
    title: "Supply House Prices That Aren't 6 Months Old",
    description:
      'Pilot syncs fixture, fitting, and material pricing so your estimates reflect what things actually cost today. No more "I\'ll eat the difference this time" moments.',
    linkLabel: "See Pricing Engine →",
    linkHref: "/features#quoting",
  },
  {
    iconName: "Siren",
    title: "Dispatch That Handles the Chaos",
    description:
      "Emergency call comes in? Pilot finds the closest available tech, routes them, notifies the customer with an ETA, and keeps you in the loop — all before you finish your coffee.",
    linkLabel: "See Dispatch →",
    linkHref: "/features#dispatch",
  },
  {
    iconName: "BarChart3",
    title: "Know If That Water Heater Job Made Money",
    description:
      "Track materials, labor, and drive time against the quoted price — in real time, not three weeks later when you finally reconcile invoices. See your margin on every job, every day.",
    linkLabel: "See Profitability →",
    linkHref: "/features#profitability",
  },
];

const voiceExamples: VoiceCard[] = [
  {
    command:
      "Quote a 40-gallon gas water heater replacement, AO Smith, standard efficiency. Customer has a Bradford White right now in the garage, direct vent.",
    response:
      "Equipment, supply lines, gas flex, expansion tank, T&P valve, permit, labor — full line-item estimate with today's pricing.",
  },
  {
    command:
      "Add a whole-house repipe, 1,800 square feet, two-bath ranch, PEX-A with Uponor fittings, crawl space access.",
    response:
      "All PEX, fittings, manifold, stub-outs, hangers, and labor generated. Material pricing current as of today.",
  },
  {
    command:
      "Emergency dispatch — slab leak at 4521 Oak Street. Send whoever's closest. Customer says water is coming through the foundation.",
    response:
      'Nearest available tech identified, routed with ETA. Customer auto-notified: "Your plumber is 22 minutes away."',
  },
];

const faqs: FAQ[] = [
  {
    question: "Can Pilot handle emergency service calls?",
    answer:
      "Yes. Pilot's dispatch board handles emergency routing — find the nearest available tech, send them the job details, notify the customer with a real-time ETA, and track the job from dispatch to invoice. You manage the chaos from your phone, not a whiteboard.",
  },
  {
    question: "Does it know actual fixture and fitting prices?",
    answer:
      "Pilot tracks real-time material pricing for fixtures, fittings, pipe, water heaters, and common plumbing materials. No more referencing a price book from six months ago. When you build a quote, the numbers are current.",
  },
  {
    question: "Can I quote a whole-house repipe by voice?",
    answer:
      "Absolutely. Walk the house, describe what you see — footage, fixture count, pipe type, access conditions — and Pilot generates the full estimate. A repipe quote that takes 2–3 hours by hand takes about 10 minutes with Pilot.",
  },
  {
    question: "I run two trucks. Is this worth it for a small shop?",
    answer:
      "That's exactly who Pilot is built for. Solo operators and 2–5 person shops lose the most time to admin because there's no dedicated office staff. Pilot handles the quoting, dispatch, and invoicing so you can run your trucks, not your paperwork.",
  },
  {
    question: "Does it sync with QuickBooks?",
    answer:
      "Bi-directional QuickBooks Online sync. Invoices, payments, and customer records flow automatically. Your bookkeeper sees everything in QuickBooks without you touching it. No double entry, no export/import dance.",
  },
  {
    question: "What about when I'm in a crawl space with zero signal?",
    answer:
      "Pilot works fully offline. Create quotes, log time, take job photos — everything queues up and syncs automatically when you get signal back. Built for crawl spaces, basements, and rural areas.",
  },
  {
    question: "Can I show my customers the estimate on-site?",
    answer:
      "Yes. Pilot generates professional PDF estimates that you can share via text, email, or show on your phone right there at the kitchen table. Three presentation styles: detailed line-item, summarized, or good/better/best options. Customers sign digitally on-site.",
  },
];

export default async function PlumbingTradePage() {
  const { mode } = await getSiteMode();
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <TradePageTemplate
        trade="plumbing"
        accentToken="--trade-plumbing"
        heroBadge="Built for Plumbing Contractors"
        heroHeadline="The AI Copilot for Plumbing Contractors"
        heroSubheadline="Your phone rings at 7 AM with a burst pipe. By 7:02, Pilot has the dispatch routed, the customer notified, and the estimate template loaded. You just drive."
        heroImageAlt="Plumber working next to water heater using Pilot dispatch interface on phone"
        painSectionHeading="The Stuff They Didn't Teach in Your Apprenticeship"
        painSectionSubtitle="You learned to sweat copper and set fixtures — not manage a business from the cab of your van."
        painPoints={painPoints}
        featureSectionHeading="What Pilot Does for Plumbers"
        featureSectionSubtitle="The back-office tools you need, built for the way plumbers actually work."
        features={features}
        voiceSectionHeading="Pilot Speaks Plumber"
        voiceSectionSubtitle="Not a generic business tool that thinks 'PVC' is a type of flooring."
        voiceExamples={voiceExamples}
        voiceBodyCopy="Pilot's Voice AI knows plumbing terminology — fixture units, pipe sizing, fitting types, and manufacturer catalogs. It builds estimates the way you think about jobs, not the way a spreadsheet does."
        pricingSectionHeading="Built for Your Plumbing Business"
        pricingBodyCopy="$49/month, everything included. Quoting, dispatch, invoicing, profitability tracking, and QuickBooks sync — one platform instead of six apps held together with duct tape. Saves 15+ hours per week in admin. That's real billable time back on the schedule."
        faqSectionHeading="Common Questions from Plumbers"
        faqs={faqs}
        finalCtaHeadline="Join the Plumbers Shaping Pilot"
        finalCtaBody="Pilot for Trades is being built with input from real plumbing contractors. Be one of the first twelve, lock in Charter pricing, and help build the tool that gives plumbers their weekends back."
        siteMode={mode}
      />
    </>
  );
}
